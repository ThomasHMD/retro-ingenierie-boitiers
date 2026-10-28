// Lit le contenu d'une autre banque du D200 par USB, puis remet la banque d'origine.
// Lancer : swift d200/outils/d200_banque.swift reglages-perso|prise-de-vue A|B|C|D [dossier de sortie]
// Nommer : swift d200/outils/d200_banque.swift nommer reglages-perso|prise-de-vue A|B|C|D "<nom>"   ("" = sans nom, comme
// d'usine) ; écrit le nom (0xD011 à 0xD014 ou 0xD041 à 0xD044 : 20 caractères complétés d'espaces), le relit, et
// garde l'ancien nom dans le journal. Le contenu de la banque n'est pas touché.
// Seule écriture : le choix de banque (SetDevicePropValue 0x1016 sur 0xD040 « banque de réglages perso » ou
// 0xD010 « banque du menu Prise de vue »), aller puis retour, vérifié par relecture. Tout le reste est lu
// (GetDevicePropDesc sur chaque réglage annoncé), avant l'aller, dans la banque visée et après le retour (avant/, apres/),
// et le journal signale tout réglage changé par l'aller-retour. Décodage : python3 d200/outils/d200_ptp.py <dossier>.
import Foundation
import ImageCaptureCore

let tous = Array(CommandLine.arguments.dropFirst())
let nommer = tous.first == "nommer"
let args = nommer ? Array(tous.dropFirst()) : tous
let codes: [String: UInt16] = ["reglages-perso": 0xD040, "prise-de-vue": 0xD010]
let nouveauNom = nommer ? (args.count > 2 ? args[2] : "") : ""
if nommer && (nouveauNom.count > 20 || !nouveauNom.allSatisfy({ $0.isASCII && !$0.isNewline })) { print("nom : 20 caractères ASCII au plus"); exit(2) }
if args.count < 2 || codes[args[0]] == nil || !["A", "B", "C", "D"].contains(args[1].uppercased()) {
    print("usage : swift d200/outils/d200_banque.swift reglages-perso|prise-de-vue A|B|C|D [dossier]"); exit(2)
}
let codeBanque: UInt16 = codes[args[0]]!
let cible = ["A", "B", "C", "D"].firstIndex(of: args[1].uppercased())!
let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let sortie = URL(fileURLWithPath: args.count > (nommer ? 3 : 2) ? args[nommer ? 3 : 2]
    : "d200/sondes/usb/banque-\(nommer ? "nom-" : "")\(args[0])-\(args[1].uppercased())-\(horodatage)")
// nom de banque : chaîne PTP de 21 caractères (20 + fin), UTF-16, complétée d'espaces comme les noms d'usine
let codeNom = codeBanque + 1 + UInt16(cible)
func chainePTP(_ s: String) -> Data {
    var d = Data([21])
    for u in (s + String(repeating: " ", count: 20 - s.count)).utf16 { d.append(UInt8(u & 0xFF)); d.append(UInt8(u >> 8)) }
    d.append(contentsOf: [0, 0]); return d
}
// valeur courante d'un descripteur STR : code(2) type(2) accès(1) défaut(1 + 2n) courant(1 + 2n)
func chaineCourante(_ d: Data) -> String? {
    let b = [UInt8](d); guard b.count > 5 else { return nil }
    let i = 6 + 2 * Int(b[5]); guard b.count > i else { return nil }
    let n = Int(b[i]); guard b.count >= i + 1 + 2 * n else { return nil }
    let u = (0..<n).map { UInt16(b[i + 1 + 2 * $0]) | UInt16(b[i + 2 + 2 * $0]) << 8 }.filter { $0 != 0 }
    return String(decoding: u, as: UTF16.self)
}

func commande(_ code: UInt16, transaction: UInt32, parametres: [UInt32] = []) -> Data {
    var d = Data()
    func ajoute<T: FixedWidthInteger>(_ v: T) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
    ajoute(UInt32(12 + 4 * parametres.count)); ajoute(UInt16(1)); ajoute(code); ajoute(transaction)
    parametres.forEach { ajoute($0) }
    return d
}
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func tableau16(_ d: Data, _ i: Int) -> [UInt16] {
    guard d.count >= i + 4 else { return [] }
    let b = [UInt8](d)
    let n = Int(b[i]) | Int(b[i + 1]) << 8 | Int(b[i + 2]) << 16 | Int(b[i + 3]) << 24
    return n > 2000 ? [] : (0..<n).map { UInt16(b[i + 4 + 2 * $0]) | UInt16(b[i + 5 + 2 * $0]) << 8 }
}
// valeur courante d'un descripteur UINT8 : code(2) type(2) accès(1) défaut(1) courant(1)
func courantU8(_ d: Data) -> Int? { d.count >= 7 ? Int(d[d.startIndex + 6]) : nil }

final class Banque: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    var origine: Int?

    func note(_ s: String) { print(s); journal.append(s) }
    func envoyer(_ code: UInt16, _ params: [UInt32] = [], donnees: Data? = nil, _ fin: @escaping (Data, UInt16) -> Void) {
        guard let b = boitier else { return }
        transaction += 1
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: donnees) { d, r, e in
            if let e { self.note("  erreur 0x\(String(code, radix: 16)) : \(e.localizedDescription)"); fin(Data(), 0) }
            else { fin(sansEntete(d), codeReponse(r)) }
        }
    }
    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("D200") else { return }   // le D40 peut être branché en même temps
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}

    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { note("Session refusée : \(error.localizedDescription)"); terminer(); return }
        try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
        envoyer(0x1001) { info, _ in
            guard info.range(of: Data([0x44, 0, 0x32, 0, 0x30, 0, 0x30, 0])) != nil else {   // « D200 » en UTF-16
                self.note("Ce n'est pas un D200 : arrêt."); self.terminer(); return
            }
            if nommer { self.renommer(); return }
            self.envoyer(0x1014, [UInt32(codeBanque)]) { v, rc in
                guard rc == 0x2001, let o = courantU8(v) else { self.note("Lecture de la banque impossible (0x\(String(rc, radix: 16)))"); self.terminer(); return }
                self.origine = o
                self.lireTout(sortie.appendingPathComponent("avant")) {
                    self.note("Banque d'origine : \("ABCD".map(String.init)[o]) ; passage sur \(args[1].uppercased())")
                    self.choisir(cible) { ok in
                        guard ok else { self.choisir(o) { _ in self.terminer() }; return }   // retour à l'origine quoi qu'il arrive
                        self.lireTout(sortie) { self.choisir(o) { _ in self.lireTout(sortie.appendingPathComponent("apres")) { self.comparer(); self.terminer() } } }
                    }
                }
            }
        }
    }
    func renommer() {
        envoyer(0x1014, [UInt32(codeNom)]) { avant, _ in
            try? avant.write(to: sortie.appendingPathComponent(String(format: "avant_%04x.bin", codeNom)))
            self.note("Banque \(args[0]) \(args[1].uppercased()) : nom actuel « \((chaineCourante(avant) ?? "?").trimmingCharacters(in: .whitespaces)) »")
            self.envoyer(0x1016, [UInt32(codeNom)], donnees: chainePTP(nouveauNom)) { _, rc in
                self.envoyer(0x1014, [UInt32(codeNom)]) { apres, _ in
                    let lu = chaineCourante(apres)?.trimmingCharacters(in: .whitespaces)
                    self.note("  nouveau nom « \(nouveauNom) » : réponse 0x\(String(rc, radix: 16)), relu « \(lu ?? "?") » : " + (rc == 0x2001 && lu == nouveauNom ? "vérifié" : "ÉCHEC"))
                    self.terminer()
                }
            }
        }
    }
    func choisir(_ banque: Int, _ fin: @escaping (Bool) -> Void) {
        envoyer(0x1016, [UInt32(codeBanque)], donnees: Data([UInt8(banque)])) { _, rc in
            self.envoyer(0x1014, [UInt32(codeBanque)]) { v, _ in
                let ok = rc == 0x2001 && courantU8(v) == banque
                self.note("  banque \("ABCD".map(String.init)[banque]) : \(ok ? "active, vérifiée" : "ÉCHEC (réponse 0x\(String(rc, radix: 16)), relu \(courantU8(v).map(String.init) ?? "?"))")")
                fin(ok)
            }
        }
    }
    // un réglage qui a changé entre avant l'aller et après le retour (hors heure, cellule, vitesse mesurée) est signalé
    func comparer() {
        let ignores: Set<String> = ["prop_5011.bin", "prop_d10a.bin", "prop_500d.bin", "prop_d100.bin"]
        let fm = FileManager.default
        let avant = sortie.appendingPathComponent("avant"), apres = sortie.appendingPathComponent("apres")
        let noms = ((try? fm.contentsOfDirectory(atPath: avant.path)) ?? []).filter { !ignores.contains($0) }.sorted()
        let changes = noms.filter { (try? Data(contentsOf: avant.appendingPathComponent($0))) != (try? Data(contentsOf: apres.appendingPathComponent($0))) }
        note(changes.isEmpty ? "Retour vérifié : tous les réglages sont comme avant." : "ATTENTION, réglages changés par l'aller-retour : \(changes.joined(separator: " "))")
    }
    func lireTout(_ dossier: URL, _ fin: @escaping () -> Void) {
        try? FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
        envoyer(0x1001) { info, _ in
            // DeviceInfo : version(2) vendeur(4) version ext(2) chaîne ext, mode(2), puis opérations, événements, réglages
            let b = [UInt8](info); var i = 8; i += 1 + 2 * Int(b[i]); i += 2
            let ops = tableau16(info, i); i += 4 + 2 * ops.count
            let ev = tableau16(info, i); i += 4 + 2 * ev.count
            let props = tableau16(info, i)
            self.envoyer(0x90CA) { v, _ in
                var file = props + tableau16(v, 0).filter { !props.contains($0) }
                self.note("  lecture de \(file.count) réglages")
                func suivant() {
                    guard !file.isEmpty else { fin(); return }
                    let c = file.removeFirst()
                    self.envoyer(0x1014, [UInt32(c)]) { d, rc in
                        if rc == 0x2001 { try? d.write(to: dossier.appendingPathComponent(String(format: "prop_%04x.bin", c))) }
                        suivant()
                    }
                }
                suivant()
            }
        }
    }
    func terminer() {
        guard !fini else { return }
        try? journal.joined(separator: "\n").write(to: sortie.appendingPathComponent("journal.txt"), atomically: true, encoding: .utf8)
        print("Résultats dans \(sortie.path)")
        boitier?.requestCloseSession(); fini = true
    }
    func device(_ device: ICDevice, didCloseSessionWithError error: Error?) {}
    func didRemove(_ device: ICDevice) {}
    func cameraDevice(_ camera: ICCameraDevice, didAdd items: [ICCameraItem]) {}
    func cameraDevice(_ camera: ICCameraDevice, didRemove items: [ICCameraItem]) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceiveThumbnail thumbnail: CGImage?, for item: ICCameraItem, error: Error?) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceiveMetadata metadata: [AnyHashable: Any]?, for item: ICCameraItem, error: Error?) {}
    func cameraDevice(_ camera: ICCameraDevice, didRenameItems items: [ICCameraItem]) {}
    func cameraDeviceDidChangeCapability(_ camera: ICCameraDevice) {}
    func cameraDevice(_ camera: ICCameraDevice, didReceivePTPEvent eventData: Data) {}
    func deviceDidBecomeReady(withCompleteContentCatalog device: ICCameraDevice) {}
    func cameraDeviceDidRemoveAccessRestriction(_ device: ICDevice) {}
    func cameraDeviceDidEnableAccessRestriction(_ device: ICDevice) {}
}

let banque = Banque()
banque.demarrer()
let limite = Date().addingTimeInterval(300), limiteRecherche = Date().addingTimeInterval(20)
while !banque.fini && Date() < limite && (banque.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if banque.boitier == nil { print("Aucun D200 trouvé : allumé (appui à mi-course s'il est en veille), câble USB, mode PTP ?") }
else if !banque.fini { print("Délai dépassé : vérifier la banque active au menu."); banque.terminer() }
