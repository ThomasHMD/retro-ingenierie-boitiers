// Écrire un Picture Control perso dans le D750 par USB (SetPictCtrlData 0x90CD), ou en effacer un (DelCstPicCtrl 0x90CE).
// Par défaut c'est une SIMULATION : l'outil lit l'emplacement, contrôle le bloc, dit ce qu'il enverrait, et n'écrit rien.
// Ajouter --ecrire pour écrire vraiment.
//   swift outils/d750_ecrire.swift ecrire <bloc.bin> <C-1 … C-9> [--ecrire] [--remplacer] [--activer]
//   swift outils/d750_ecrire.swift effacer <C-1 … C-9> [--ecrire]
// bloc.bin : python3 outils/picture_control.py bloc <recette.json> <bloc.bin>   (32 octets, ou 610 avec la courbe perso)
// Format, commandes et preuves : recherche/d750-picture-control-usb.md (§4 et §6).
// Garde-fous : emplacements perso C-1 à C-9 seulement, jamais les Picture Control d'usine ; un emplacement occupé est refusé
// sans --remplacer (0x90CD avec ModifiedFlag 0 l'écraserait sans prévenir) ; refus si le boîtier n'est pas un D750 ;
// l'ancien contenu est sauvé avant d'écrire ; après, relecture (réglage courant et défaut) comparée à l'envoi.
// --activer : choisit ensuite ce Picture Control (SetDevicePropValue 0xD200), une écriture de plus.
// Rien d'autre n'est écrit : ni firmware, ni autre réglage. Journal : sondes/d750/usb/ecriture-<date>/.
// Phase de données sortante : la charge utile seule, sans l'entête PTP de 12 octets (usage d'ImageCaptureCore dans les
// projets publics, par exemple Obscura) ; si macOS la cadrait autrement, l'octet 0 lu par le boîtier ne serait plus une base
// valide et il refuserait le bloc (0x201D), sans rien écrire.
import Foundation
import ImageCaptureCore

let racine = "sondes/d750/usb"
let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let sortie = URL(fileURLWithPath: "\(racine)/ecriture-\(horodatage)")
let arguments = Array(CommandLine.arguments.dropFirst().filter { !$0.hasPrefix("--") })
let options = Set(CommandLine.arguments.filter { $0.hasPrefix("--") })
let pourDeVrai = options.contains("--ecrire")
let reponses: [UInt16: String] = [0x2001: "OK", 0x2002: "erreur générale", 0x2006: "paramètres non pris en charge",
                                  0x2007: "transfert incomplet", 0x200F: "accès refusé (U1/U2 ou réglage verrouillé ?)",
                                  0x2019: "boîtier occupé (prise de vue en cours ?)", 0x201D: "paramètre ou bloc refusé"]

func usage() -> Never {
    print("""
    swift outils/d750_ecrire.swift ecrire <bloc.bin> <C-1 … C-9> [--ecrire] [--remplacer] [--activer]
    swift outils/d750_ecrire.swift effacer <C-1 … C-9> [--ecrire]
    Sans --ecrire : simulation, rien n'est écrit.
    """)
    exit(2)
}
func numero(_ s: String) -> UInt32 {
    let n = Int(s.uppercased().replacingOccurrences(of: "C-", with: "").replacingOccurrences(of: "C", with: "")) ?? 0
    guard (1...9).contains(n) else { print("Emplacement « \(s) » : C-1 à C-9 seulement."); exit(2) }
    return UInt32(200 + n)
}
// contrôle de forme du bloc ; les plages de valeurs sont vérifiées par picture_control.py puis par le boîtier
func controle(_ b: Data) -> String? {
    let o = { (i: Int) in b[b.startIndex + i] }
    guard b.count == 32 || b.count == 610 else { return "\(b.count) octets : 32 ou 610 attendus" }
    guard (1...7).contains(o(0)) else { return "octet 0 (base) = \(o(0)) : 1 à 7 attendu" }
    guard o(1) == (o(0) == 4 ? 1 : 0) else { return "octet 1 (monochrome) incohérent avec la base" }
    guard o(2) == 1 else { return "octet 2 = \(o(2)) : 1 (perso) obligatoire pour C-1 à C-9" }
    guard (3..<23).allSatisfy({ o($0) == 0 || (0x20..<0x7F).contains(o($0)) }), o(22) == 0, o(3) != 0 else { return "nom (octets 3 à 22) invalide" }
    guard o(0) == 4 || o(23) == 0 else { return "octet 23 : accentuation rapide interdite sur un Picture Control perso" }
    guard o(31) == (b.count == 610 ? 1 : 0) else { return "octet 31 (courbe) incohérent avec la longueur" }
    guard b.count == 32 || (o(32) == 0x49 && o(33) == 0x30) else { return "courbe : entête « I0 » attendu (octets 32 et 33)" }
    return nil
}
func nomDe(_ v: Data) -> String { v.count >= 23 ? String(decoding: v.subdata(in: (v.startIndex + 3)..<(v.startIndex + 23)).prefix { $0 != 0 }, as: UTF8.self) : "" }
func genre(_ v: Data) -> Int { v.count >= 3 ? Int(v[v.startIndex + 2]) : -1 }   // 0 usine, 1 perso, 2 vide
func ecarts(_ a: Data, _ b: Data) -> [Int] {
    guard a.count == b.count else { return [-1] }
    let courbe = a.count == 610
    return (0..<a.count).filter { a[a.startIndex + $0] != b[b.startIndex + $0] && !(courbe && ($0 == 28 || $0 == 29)) }
}

struct Lecteur {
    let d: Data; var i = 0
    init(_ d: Data) { self.d = d }
    mutating func u8() -> UInt8 { defer { i += 1 }; return i < d.count ? d[d.startIndex + i] : 0 }
    mutating func u16() -> UInt16 { UInt16(u8()) | UInt16(u8()) << 8 }
    mutating func u32() -> UInt32 { UInt32(u16()) | UInt32(u16()) << 16 }
    mutating func tableau16() -> [UInt16] { let n = Int(u32()); return n > 2000 ? [] : (0..<n).map { _ in u16() } }
    mutating func chaine() -> String {
        let n = Int(u8()); var c: [UInt16] = []
        for _ in 0..<n { c.append(u16()) }
        return String(decoding: c.filter { $0 != 0 }, as: UTF16.self)
    }
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
func texte(_ rc: UInt16) -> String { String(format: "0x%04x", rc) + " " + (reponses[rc] ?? "?") }


func chainePTP(_ t: String) -> Data {
    let c = Array(t.padding(toLength: 36, withPad: " ", startingAt: 0).utf16) + [0]
    var d = Data([UInt8(c.count)]); c.forEach { withUnsafeBytes(of: $0.littleEndian) { d.append(contentsOf: $0) } }; return d
}
func lireChaine(_ v: Data) -> String { var l = Lecteur(v); return l.chaine().trimmingCharacters(in: .whitespaces) }
let commentaires: [(UInt16, String)] = [(0xD021, "KODACHROME 6250K"), (0xD022, "TRI-X 10000K"), (0xD023, "PORTRA 400 5600K")]
final class Ecriture: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    func note(_ s: String) { print(s); journal.append(s) }
    func garde(_ v: Data, _ nom: String) { try? v.write(to: sortie.appendingPathComponent(nom)) }
    func envoyer(_ code: UInt16, _ params: [UInt32], donnees: Data? = nil, _ fin: @escaping (Data, UInt16) -> Void) {
        guard let b = boitier else { return }
        transaction += 1
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: donnees) { d, r, e in
            DispatchQueue.main.async {
                if let e { self.note("  0x\(String(code, radix: 16)) : erreur \(e.localizedDescription)"); fin(Data(), 0) }
                else { fin(sansEntete(d), codeReponse(r)) }
            }
        }
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("D750") else { return }   // le D40 peut être branché en même temps
        print("Boîtier trouvé : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}

    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
        envoyer(0x1001, []) { p, _ in
            var l = Lecteur(p)
            _ = l.u16(); _ = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
            _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16()
            _ = l.chaine(); let modele = l.chaine()
            guard modele.contains("D750") else { self.arreter("Ce n'est pas un D750 : arrêt."); return }
            self.suite(0)
        }
    }
    func suite(_ i: Int) {
        guard i < commentaires.count else { arreter("Terminé."); return }
        let (code, t) = commentaires[i]
        envoyer(0x1015, [UInt32(code)]) { avant, _ in
            self.garde(avant, "avant_\(String(code, radix: 16)).bin")
            self.envoyer(0x1016, [UInt32(code)], donnees: chainePTP(t)) { _, rc in
                self.envoyer(0x1015, [UInt32(code)]) { apres, _ in
                    self.note("0x\(String(code, radix: 16, uppercase: true)) : « \(lireChaine(avant)) » → \(texte(rc)) → relu « \(lireChaine(apres)) »")
                    self.suite(i + 1)
                }
            }
        }
    }
    func arreter(_ message: String) {
        note(message)
        try? journal.joined(separator: "\n").write(to: sortie.appendingPathComponent("journal.txt"), atomically: true, encoding: .utf8)
        print("Journal et copies dans \(sortie.path)")
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

let travail = Ecriture()
travail.demarrer()
let limite = Date().addingTimeInterval(60)
let limiteRecherche = Date().addingTimeInterval(20)
while !travail.fini && Date() < limite && (travail.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if travail.boitier == nil { print("Aucun boîtier trouvé : allumé, câble USB branché ? Fermer Photos et Transfert d'images s'ils s'ouvrent.") }
else if !travail.fini { travail.arreter("Pas de réponse complète du boîtier dans les 60 s : relancer d'abord sans --ecrire pour voir l'état de l'emplacement.") }
