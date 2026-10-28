// Test USB du D750, en lecture seule : ce que le boîtier dit de ses Picture Control, courbe perso comprise.
// Lancer : swift outils/d750_ptp.swift [dossier de sortie]   (boîtier allumé, branché en USB).
// N'envoie que des commandes de lecture : GetDeviceInfo (0x1001), GetVendorPropCodes (0x90CA), GetDevicePropDesc (0x1014)
// sur quelques réglages, GetPictCtrlData (0x90CC) et GetPicCtrlCapability (0x90CF) sur chaque Picture Control, et la variante
// à trois paramètres 0x940D (même code de lecture que 0x90CC dans le firmware). Rien n'est écrit dans le boîtier.
// Format et preuves (firmware C 1.15, doc USB du SDK Nikon) : recherche/d750-picture-control-usb.md.
//   0x90CC(n, p2) : n = 1 à 7 (usine), 201 à 209 (C-1 à C-9) ; p2 = 0 valeur courante, 1 valeur par défaut ; exactement deux
//   paramètres. Réponse : 32 octets, ou 610 si l'octet 31 vaut 1 (courbe perso, 578 octets comme dans un NCP).
//   0x90CF(n) : 39 octets. 0x940D(n, p2, mode) : mode 0 ou 1 (1 = menu vidéo, hypothèse).
// Décodage d'un bloc : python3 outils/picture_control.py ptp <pictctrl_n_p.bin>
import Foundation
import ImageCaptureCore

let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let sortie = URL(fileURLWithPath: CommandLine.arguments.count > 1 ? CommandLine.arguments[1]
    : URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        .appendingPathComponent("sondes/d750/usb/\(horodatage)").path)   // hors git (.gitignore)
let cherchees: [UInt16: String] = [0x90CC: "GetPictCtrlData (lire un Picture Control)", 0x90CD: "SetPictCtrlData (écrire un Picture Control)",
                                   0x90CE: "DelCstPicCtrl (effacer un Picture Control perso)", 0x90CF: "GetPicCtrlCapability",
                                   0x90C5: "CurveDownload (lire la courbe perso)", 0x90C6: "CurveUpload (envoyer la courbe perso)",
                                   0x100E: "InitiateCapture (déclencher)", 0x9207: "InitiateCaptureRecInMedia (déclencher sur la carte)",
                                   0x90CA: "GetVendorPropCodes", 0x940D: "variante de GetPictCtrlData à 3 paramètres",
                                   0x1014: "GetDevicePropDesc", 0x1016: "SetDevicePropValue"]
let reglages: [UInt16: String] = [0x5004: "qualité", 0x5005: "balance des blancs", 0x500E: "mode d'exposition", 0x500F: "ISO",
                                  0xD01E: "température de couleur", 0xD032: "espace colorimétrique", 0xD070: "réduction du bruit ISO",
                                  0xD0FC: "mode utilisateur", 0xD14E: "D-Lighting actif", 0xD200: "Picture Control actif",
                                  0xD201: "Picture Control à modifier"]
let numeros: [UInt32] = Array(1...7) + Array(201...209)

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
// selon la version de macOS, la phase de données peut garder l'entête PTP de 12 octets
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func decrit(_ v: Data) -> String {
    guard v.count >= 32 else { return "\(v.count) octets, trop court" }
    let o = { (i: Int) in v[v.startIndex + i] }
    let nom = String(decoding: v.subdata(in: (v.startIndex + 3)..<(v.startIndex + 23)).prefix { $0 != 0 }, as: UTF8.self)
    let genre = ["usine", "perso", "vide"][min(Int(o(2)), 2)]
    let courbe = o(31) == 1 ? (v.count == 610 ? "courbe perso (610 octets)" : "drapeau de courbe mais \(v.count) octets") : "sans courbe"
    return "\(v.count) octets | base \(o(0)) | \(genre) | « \(nom) » | \(courbe)"
}
func hexa(_ d: Data, _ n: Int = 48) -> String { d.prefix(n).map { String(format: "%02x", $0) }.joined(separator: " ") + (d.count > n ? " …" : "") }

final class Test: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var file: [() -> Void] = []
    var resume: [String] = []

    func note(_ s: String) { print(s); resume.append(s) }
    func suivant() { DispatchQueue.main.async { if self.file.isEmpty { self.terminer() } else { self.file.removeFirst()() } } }
    func envoyer(_ code: UInt16, _ params: [UInt32] = [], _ fin: @escaping (Data, UInt16) -> Void) {
        guard let b = boitier else { return }
        transaction += 1
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: nil) { donnees, reponse, erreur in
            if let erreur { self.note("  0x\(String(code, radix: 16)) \(params) : erreur \(erreur.localizedDescription)"); fin(Data(), 0) }
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
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("D750") else { return }   // le D40 peut être branché en même temps
        print("Boîtier trouvé : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}

    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
        envoyer(0x1001) { p, _ in
            try? p.write(to: sortie.appendingPathComponent("deviceinfo.bin"))
            var l = Lecteur(p)
            _ = l.u16(); let vendeur = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
            let ops = Set(l.tableau16()); _ = l.tableau16(); let props = Set(l.tableau16()); _ = l.tableau16(); _ = l.tableau16()
            let fabricant = l.chaine(), modele = l.chaine(), version = l.chaine()
            self.note("Fabricant : \(fabricant) | modèle : \(modele) | firmware : \(version) | extension : 0x\(String(vendeur, radix: 16))")
            self.note("Commandes annoncées : \(ops.count), réglages annoncés : \(props.count)")
            for code in cherchees.keys.sorted() { self.note("  0x\(String(code, radix: 16, uppercase: true)) \(cherchees[code]!) : \(ops.contains(code) ? "OUI" : "non")") }
            // les réglages Nikon (0xDxxx) n'apparaissent pas dans DeviceInfo : il faut GetVendorPropCodes
            func lireReglages(_ annonces: Set<UInt16>) {
                guard ops.contains(0x1014) else { return }
                for code in reglages.keys.sorted() where annonces.contains(code) {
                    self.file.append { self.envoyer(0x1014, [UInt32(code)]) { v, rc in
                        try? v.write(to: sortie.appendingPathComponent("prop_\(String(code, radix: 16)).bin"))
                        let modifiable = v.count > 4 ? (v[v.startIndex + 4] == 1 ? "modifiable" : "lecture seule") : "?"
                        self.note("  réglage 0x\(String(code, radix: 16, uppercase: true)) \(reglages[code]!) : \(rc == 0x2001 ? "\(modifiable) | \(hexa(v, 24))" : String(format: "refusé (0x%04x)", rc))") } }
                }
            }
            lireReglages(props)
            if ops.contains(0x90CA) {
                self.file.append { self.envoyer(0x90CA) { v, rc in
                    try? v.write(to: sortie.appendingPathComponent("vendorprops.bin"))
                    var lv = Lecteur(v); let codesNikon = Set(lv.tableau16())
                    self.note("  réglages Nikon annoncés (0x90CA) : \(codesNikon.count) \(rc == 0x2001 ? "" : String(format: "(réponse 0x%04x)", rc))")
                    lireReglages(codesNikon)
                } }
            }
            if ops.contains(0x90CC) {
                for n in numeros { for p2: UInt32 in [0, 1] {
                    self.file.append { self.envoyer(0x90CC, [n, p2]) { v, rc in
                        if rc == 0x2001, !v.isEmpty {
                            try? v.write(to: sortie.appendingPathComponent("pictctrl_\(n)_\(p2).bin"))
                            self.note("  Picture Control \(n), paramètre \(p2) : \(decrit(v)) | \(hexa(v))")
                        } else { self.note("  Picture Control \(n), paramètre \(p2) : \(String(format: "réponse 0x%04x", rc))") }
                    } }
                } }
            }
            if ops.contains(0x90CF) {
                for n in numeros {
                    self.file.append { self.envoyer(0x90CF, [n]) { v, rc in
                        if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("picctrlcap_\(n).bin")) }
                        self.note("  capacités \(n) (0x90CF) : \(rc == 0x2001 ? "\(v.count) octets | \(hexa(v, 39))" : String(format: "réponse 0x%04x", rc))")
                    } }
                }
            }
            if ops.contains(0x940D) {
                for n in numeros { for mode: UInt32 in [0, 1] {
                    self.file.append { self.envoyer(0x940D, [n, 0, mode]) { v, rc in
                        if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("pictctrl940d_\(n)_\(mode).bin")) }
                        self.note("  0x940D \(n), mode \(mode) : \(rc == 0x2001 ? decrit(v) : String(format: "réponse 0x%04x", rc))")
                    } }
                } }
            }
            self.note(ops.contains(0x90CD) ? "Verdict : le D750 annonce l'écriture des Picture Control par USB." : "Verdict : pas d'écriture annoncée par USB, on reste sur la carte.")
        }
    }
    func terminer() {
        guard !fini else { return }
        try? resume.joined(separator: "\n").write(to: sortie.appendingPathComponent("resume.txt"), atomically: true, encoding: .utf8)
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

let test = Test()
test.demarrer()
let limite = Date().addingTimeInterval(240)
let limiteRecherche = Date().addingTimeInterval(20)
while !test.fini && Date() < limite && (test.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if test.boitier == nil { print("Aucun boîtier trouvé : allumé, câble USB branché, carte dedans ? Fermer Photos et Transfert d'images s'ils s'ouvrent.") }
else if !test.fini { print("Pas de réponse complète du boîtier dans les 240 s."); test.terminer() }
