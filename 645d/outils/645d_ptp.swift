// Sonde USB du Pentax 645D, en lecture seule : tout ce que le boîtier annonce, chaque réglage avec sa plage et sa valeur.
// Lancer : swift 645d/outils/645d_ptp.swift [dossier de sortie] [--balayage]   (boîtier allumé, USB en mode PTP, Photos et Transfert d'images fermés).
// --balayage : GetDevicePropDesc aussi sur les codes non annoncés 0x5000-0x50FF et 0xD000-0xD2FF (réglages cachés), toujours en lecture.
// --constructeur : ouvre le mode constructeur Pentax (0x9001 SetPentaxVendorMode 0x0D, 0x12E08, 1 : change le mode de connexion,
// aucun réglage), relit DeviceInfo, les propriétés annoncées et les 52 codes attendus, GetAllConditions (0x900F), puis referme
// ce mode (0x9001 … 0) en fin de sonde. Avec --balayage aussi, le balayage se fait dans le mode constructeur.
// Sorties : resume.txt, proprietes.tsv (descripteurs décodés), prop_*.bin / c_prop_*.bin (bruts), getallconditions_900f.bin.
// Analyse du firmware 1.33 qui justifie cette poignée de main : 645d/recherche/645d-firmware-usb.md ; résultats : 645d/recherche/645d-usb-et-reglages.md.
// N'envoie que des commandes de lecture : GetDeviceInfo (0x1001), GetStorageIDs (0x1004), GetStorageInfo (0x1005),
// GetDevicePropDesc (0x1014), GetDevicePropValue (0x1015), GetAllConditions (0x900F). Rien n'est écrit dans le boîtier. Thomas : jamais de modification du firmware du 645D.
// Repris de d200_ptp.swift (même mécanique ImageCaptureCore). D750 et D200 peuvent être branchés en même temps : filtre « 645D ».
import Foundation
import ImageCaptureCore

let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let arguments = CommandLine.arguments.dropFirst().filter { !$0.hasPrefix("--") }
let balayage = CommandLine.arguments.contains("--balayage")
let constructeur = CommandLine.arguments.contains("--constructeur")
let sortie = URL(fileURLWithPath: !arguments.isEmpty ? arguments.first!
    : "645d/sondes/usb/\(horodatage)")
// codes autorisés : uniquement des lectures (garde-fou contre une faute de frappe dans la file)
// 0x9001 : mode de connexion seulement, avec --constructeur ; 0x900F GetAllConditions : relit l'état (bloc [00 08]), sans effet
let lectures: Set<UInt16> = [0x1001, 0x1004, 0x1005, 0x1014, 0x1015, 0x9001, 0x900F]
// 1.33 annonce toujours 5 réglages en mode constructeur (sonde d’octobre 2026) : on demande donc aussi, un par un, les 52 codes
// de la liste du firmware (0xa82c, 645d/recherche/645d-firmware-usb.md §4)
let attendus: [UInt16] = [0x5004, 0x5005, 0x5007, 0x5008] + Array(0x500A...0x5015) + [0x501C, 0x501E, 0x501F]
    + Array(0xD001...0xD006) + Array(0xD011...0xD017) + [0xD01A, 0xD01B, 0xD01F] + Array(0xD020...0xD032)
let nomsTypes: [UInt16: String] = [1: "INT8", 2: "UINT8", 3: "INT16", 4: "UINT16", 5: "INT32", 6: "UINT32", 7: "INT64", 8: "UINT64", 0xFFFF: "STR"]
func tailleType(_ t: UInt16) -> Int { [1: 1, 2: 1, 3: 2, 4: 2, 5: 4, 6: 4, 7: 8, 8: 8][Int(t & 0x0FFF)] ?? 0 }

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
    mutating func valeur(_ t: UInt16) -> String {
        if t == 0xFFFF { return "« \(chaine()) »" }
        if t & 0x4000 != 0 { let n = Int(u32()); return "[" + (0..<min(n, 200)).map { _ in valeur(t & 0x0FFF) }.joined(separator: " ") + "]" }
        switch t {
        case 1: return "\(Int8(bitPattern: u8()))"
        case 3: return "\(Int16(bitPattern: u16()))"
        case 5: return "\(Int32(bitPattern: u32()))"
        case 7, 8: let a = u32(), b = u32(); return String(format: "0x%08X%08X", b, a)
        default: let n = tailleType(t); return n == 1 ? "\(u8())" : n == 2 ? "\(u16())" : n == 4 ? "\(u32())" : "?"
        }
    }
}
// descripteur PTP : code(2) type(2) accès(1) défaut courant forme(1) [plage min max pas | énumération n(2) valeurs]
func decrireDescripteur(_ v: Data) -> String {
    var l = Lecteur(v); _ = l.u16(); let t = l.u16(); let acces = l.u8()
    guard t == 0xFFFF || t & 0x4000 != 0 || tailleType(t) > 0 else { return "type 0x\(String(t, radix: 16)) inconnu\t\t\t\t" }
    let defaut = l.valeur(t), courant = l.valeur(t), forme = l.u8()
    let f = forme == 1 ? "plage \(l.valeur(t)) à \(l.valeur(t)) pas \(l.valeur(t))"
        : forme == 2 ? { () -> String in let n = Int(l.u16()); return "liste " + (0..<min(n, 300)).map { _ in l.valeur(t) }.joined(separator: " ") }()
        : forme == 0 ? "" : "forme \(forme)"
    return "\(nomsTypes[t] ?? (t & 0x4000 != 0 ? "A" + (nomsTypes[t & 0x0FFF] ?? "?") : "?"))\t\(acces == 1 ? "RW" : "R")\t\(defaut)\t\(courant)\t\(f)"
}

func commande(_ code: UInt16, transaction: UInt32, parametres: [UInt32] = []) -> Data {
    var d = Data()
    func ajoute<T: FixedWidthInteger>(_ v: T) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
    ajoute(UInt32(12 + 4 * parametres.count)); ajoute(UInt16(1)); ajoute(code); ajoute(transaction)
    parametres.forEach { ajoute($0) }
    return d
}
// selon la version de macOS, la phase de données peut garder l'entête PTP de 12 octets
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func hexa(_ d: Data, _ n: Int = 48) -> String { d.prefix(n).map { String(format: "%02x", $0) }.joined(separator: " ") + (d.count > n ? " …" : "") }
func h4(_ c: UInt16) -> String { String(format: "0x%04X", c) }

final class Sonde: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var file: [() -> Void] = []
    var resume: [String] = []
    var ops: Set<UInt16> = []
    var table: [String] = ["mode\tcode\tréponse\ttype\taccès\tdéfaut\tcourant\tforme\tvaleur (0x1015)"]
    var types: [UInt16: UInt16] = [:]

    func note(_ s: String) { print(s); resume.append(s) }
    func suivant() { DispatchQueue.main.async { if self.file.isEmpty { self.terminer() } else { self.file.removeFirst()() } } }
    func envoyer(_ code: UInt16, _ params: [UInt32] = [], _ fin: @escaping (Data, UInt16) -> Void) {
        guard let b = boitier else { return }
        guard lectures.contains(code) else { note("  \(h4(code)) refusé par la sonde (pas une lecture)"); suivant(); return }
        transaction += 1
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: nil) { donnees, reponse, erreur in
            if let erreur { self.note("  \(h4(code)) \(params) : erreur \(erreur.localizedDescription)"); fin(Data(), 0) }
            else { fin(sansEntete(donnees), codeReponse(reponse)) }
            self.suivant()
        }
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        print("Vu : \(device.name ?? "?")")
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").uppercased().contains("645D"), !(b.transportType ?? "").contains("MassStorage") else { return }   // D750 et D200 peuvent être branchés en même temps
        print("Boîtier retenu : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}

    // silencieux : n'écrit au résumé que les codes qui répondent (balayage de 1 000 codes)
    func lireReglages(_ codes: [UInt16], _ origine: String, silencieux: Bool = false) {
        guard ops.contains(0x1014) else { note("  GetDevicePropDesc non annoncée : réglages non lus"); return }
        let prefixe = origine.hasPrefix("constructeur") ? "c_" : ""
        for code in codes {
            file.append { self.envoyer(0x1014, [UInt32(code)]) { v, rc in
                if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("\(prefixe)prop_\(String(format: "%04x", code)).bin")) }
                if rc == 0x2001, v.count > 4 {
                    self.types[code] = UInt16(v[v.startIndex + 2]) | UInt16(v[v.startIndex + 3]) << 8
                    let d = decrireDescripteur(v)
                    self.table.append("\(origine)\t\(h4(code))\t0x2001\t\(d)")
                    self.note("  \(origine) \(h4(code)) : \(d.replacingOccurrences(of: "\t", with: " | "))")
                } else if !silencieux {
                    self.table.append("\(origine)\t\(h4(code))\t\(String(format: "0x%04x", rc))\t\t\t\t\t")
                    self.note("  \(origine) \(h4(code)) : \(String(format: "réponse 0x%04x", rc))\(v.isEmpty ? "" : " | \(hexa(v, 24))")")
                }
            } }
            // valeur courante : les réglages en lecture seule (balance des blancs, ouverture…) ont un descripteur sans valeur
            file.append {
                guard let t = self.types[code] else { self.suivant(); return }
                self.envoyer(0x1015, [UInt32(code)]) { v, rc in
                    if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("\(prefixe)val_\(String(format: "%04x", code)).bin")) }
                    var l = Lecteur(v)
                    let s = rc != 0x2001 ? String(format: "réponse 0x%04x", rc) : (t == 0 || (tailleType(t) == 0 && t != 0xFFFF && t & 0x4000 == 0)) ? "brut \(hexa(v, 64))" : l.valeur(t)
                    self.table[self.table.count - 1] += "\t\(s)"
                    self.note("    valeur \(h4(code)) : \(s)")
                }
            }
        }
    }

    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
        envoyer(0x1001) { p, rc in
            try? p.write(to: sortie.appendingPathComponent("deviceinfo.bin"))
            var l = Lecteur(p)
            _ = l.u16(); let vendeur = l.u32(); let vversion = l.u16(); let vdesc = l.chaine(); _ = l.u16()
            self.ops = Set(l.tableau16()); let evenements = l.tableau16(); let props = l.tableau16(); let capture = l.tableau16(); let formats = l.tableau16()
            let fabricant = l.chaine(), modele = l.chaine(), version = l.chaine()
            self.note("Fabricant : \(fabricant) | modèle : \(modele) | firmware : \(version) | extension : 0x\(String(vendeur, radix: 16)) v\(vversion) « \(vdesc) » | réponse \(String(format: "0x%04x", rc))")
            guard modele.uppercased().contains("645D") else { self.note("Ce n'est pas un 645D : arrêt."); return }
            self.note("Commandes annoncées : \(self.ops.count), événements : \(evenements.count), réglages : \(props.count)")
            self.note("  commandes : " + self.ops.sorted().map(h4).joined(separator: " "))
            self.note("  événements : " + evenements.map(h4).joined(separator: " "))
            self.note("  réglages : " + props.map(h4).joined(separator: " "))
            self.note("  formats de capture : " + capture.map(h4).joined(separator: " ") + " | formats d'image : " + formats.map(h4).joined(separator: " "))
            self.lireReglages(props, "annoncé")
            if balayage && !constructeur {
                let connus = Set(props)
                self.lireReglages(Array(0x5000...0x50FF).map(UInt16.init).filter { !connus.contains($0) }
                                  + Array(0xD000...0xD2FF).map(UInt16.init).filter { !connus.contains($0) }, "caché ?", silencieux: true)
            }
            if constructeur && self.ops.contains(0x9001) {
                self.file.append { self.envoyer(0x9001, [0x0D, 0x12E08, 1]) { _, rc in
                    self.note("SetPentaxVendorMode 0x9001 (0x0D, 0x12E08, 1) : \(String(format: "réponse 0x%04x", rc))")
                    guard rc == 0x2001 else { return }
                    let avant = self.file; self.file = []
                    self.file.append { self.envoyer(0x1001) { p2, _ in
                        try? p2.write(to: sortie.appendingPathComponent("deviceinfo-constructeur.bin"))
                        var l2 = Lecteur(p2)
                        _ = l2.u16(); _ = l2.u32(); _ = l2.u16(); _ = l2.chaine(); _ = l2.u16()
                        let ops2 = l2.tableau16(); _ = l2.tableau16(); let props2 = l2.tableau16()
                        self.ops.formUnion(ops2)
                        self.note("Mode constructeur : \(ops2.count) commandes, \(props2.count) réglages")
                        self.note("  commandes : " + ops2.sorted().map(h4).joined(separator: " "))
                        self.note("  réglages : " + props2.map(h4).joined(separator: " "))
                        let reste = self.file; self.file = []
                        self.lireReglages(props2, "constructeur")
                        let annonces = Set(props2)
                        self.lireReglages(attendus.filter { !annonces.contains($0) }, "constructeur attendu")
                        if balayage {
                            let connus = annonces.union(attendus)
                            self.lireReglages(Array(0x5000...0x50FF).map(UInt16.init).filter { !connus.contains($0) }
                                              + Array(0xD000...0xD2FF).map(UInt16.init).filter { !connus.contains($0) }, "constructeur caché ?", silencieux: true)
                        }
                        if ops2.contains(0x900F) {
                            self.file.append { self.envoyer(0x900F) { v, rc in
                                if !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("getallconditions_900f.bin")) }
                                self.note("GetAllConditions 0x900F : \(String(format: "réponse 0x%04x", rc)), \(v.count) octets | \(hexa(v, 32))")
                            } }
                        }
                        self.file += reste
                        self.file.append { self.envoyer(0x9001, [0x0D, 0x12E08, 0]) { _, rc0 in
                            self.note("Fin : mode constructeur refermé (0x9001 … 0) : \(String(format: "réponse 0x%04x", rc0))") } }
                    } }
                    self.file += avant
                } }
            }
            if self.ops.contains(0x1004) {
                self.file.append { self.envoyer(0x1004) { v, rc in self.note("Stockages (0x1004) : \(rc == 0x2001 ? hexa(v) : String(format: "réponse 0x%04x", rc))") } }
            }
        }
    }
    func terminer() {
        guard !fini else { return }
        try? resume.joined(separator: "\n").write(to: sortie.appendingPathComponent("resume.txt"), atomically: true, encoding: .utf8)
        try? table.joined(separator: "\n").write(to: sortie.appendingPathComponent("proprietes.tsv"), atomically: true, encoding: .utf8)
        print("Résultats dans \(sortie.path)")
        boitier?.requestCloseSession(); fini = true
    }
    func device(_ device: ICDevice, didCloseSessionWithError error: Error?) {}
    func didRemove(_ device: ICDevice) {}

    // le reste du protocole : rien à faire ici
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

let sonde = Sonde()
sonde.demarrer()
let limite = Date().addingTimeInterval(300)
let limiteRecherche = Date().addingTimeInterval(20)
while !sonde.fini && Date() < limite && (sonde.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if sonde.boitier == nil { print("Aucun 645D trouvé : allumé (appui à mi-course s'il est en veille), câble USB branché, mode PTP ? Fermer Photos et Transfert d'images.") }
else if !sonde.fini { print("Pas de réponse complète du boîtier dans les 300 s."); sonde.terminer() }
