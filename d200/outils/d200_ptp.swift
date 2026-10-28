// Sonde USB du D200, en lecture seule : tout ce que le boîtier annonce, chaque réglage avec sa plage, et la courbe perso.
// Lancer : swift d200/outils/d200_ptp.swift [dossier de sortie] [--balayage]   (boîtier allumé, USB en mode PTP, Photos et Transfert d'images fermés).
// --balayage : GetDevicePropDesc aussi sur les codes non annoncés 0x5000-0x50FF et 0xD000-0xD2FF (réglages cachés), toujours en lecture.
// N'envoie que des commandes de lecture : GetDeviceInfo (0x1001), GetVendorPropCodes (0x90CA), GetDevicePropDesc (0x1014)
// sur chaque réglage annoncé (standard et Nikon), et CurveDownload (0x90C5, courbe perso du boîtier vers le Mac).
// Rien n'est écrit dans le boîtier : ni SetDevicePropValue (0x1016), ni CurveUpload (0x90C6).
// Décodage des fichiers : python3 d200/outils/d200_ptp.py <dossier>. Résultats : d200/recherche/d200-ptp-usb.md.
import Foundation
import ImageCaptureCore

let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let arguments = CommandLine.arguments.dropFirst().filter { $0 != "--balayage" }
let balayage = CommandLine.arguments.contains("--balayage")
let sortie = URL(fileURLWithPath: !arguments.isEmpty ? arguments.first!
    : "d200/sondes/usb/\(horodatage)")
// codes autorisés : uniquement des lectures (garde-fou contre une faute de frappe dans la file)
let lectures: Set<UInt16> = [0x1001, 0x90CA, 0x1014, 0x90C5]

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
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").contains("D200") else { return }   // le D40 peut être branché en même temps
        print("Boîtier retenu : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}

    func lireReglages(_ codes: [UInt16], _ origine: String) {
        guard ops.contains(0x1014) else { note("  GetDevicePropDesc non annoncée : réglages non lus"); return }
        for code in codes {
            file.append { self.envoyer(0x1014, [UInt32(code)]) { v, rc in
                if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent("prop_\(String(format: "%04x", code)).bin")) }
                let acces = v.count > 4 ? (v[v.startIndex + 4] == 1 ? "écriture" : "lecture") : "?"
                self.note("  \(origine) \(h4(code)) : \(rc == 0x2001 ? "\(acces) | \(hexa(v, 24))" : String(format: "réponse 0x%04x", rc))")
            } }
        }
    }

    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
        envoyer(0x1001) { p, rc in
            try? p.write(to: sortie.appendingPathComponent("deviceinfo.bin"))
            var l = Lecteur(p)
            _ = l.u16(); let vendeur = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
            self.ops = Set(l.tableau16()); let evenements = l.tableau16(); let props = l.tableau16(); _ = l.tableau16(); _ = l.tableau16()
            let fabricant = l.chaine(), modele = l.chaine(), version = l.chaine()
            self.note("Fabricant : \(fabricant) | modèle : \(modele) | firmware : \(version) | extension : 0x\(String(vendeur, radix: 16)) | réponse \(String(format: "0x%04x", rc))")
            guard modele.contains("D200") else { self.note("Ce n'est pas un D200 : arrêt."); return }
            self.note("Commandes annoncées : \(self.ops.count), événements : \(evenements.count), réglages standard : \(props.count)")
            self.note("  commandes : " + self.ops.sorted().map(h4).joined(separator: " "))
            self.note("  réglages standard : " + props.map(h4).joined(separator: " "))
            self.lireReglages(props, "standard")
            if self.ops.contains(0x90CA) {
                self.file.append { self.envoyer(0x90CA) { v, rc in
                    try? v.write(to: sortie.appendingPathComponent("vendorprops.bin"))
                    var lv = Lecteur(v); let codesNikon = lv.tableau16()
                    self.note("Réglages Nikon annoncés (0x90CA) : \(codesNikon.count) \(rc == 0x2001 ? "" : String(format: "(réponse 0x%04x)", rc))")
                    self.note("  " + codesNikon.map(h4).joined(separator: " "))
                    // ajoutés en tête de file : la courbe reste en dernier
                    let avant = self.file; self.file = []
                    self.lireReglages(codesNikon.filter { !props.contains($0) }, "Nikon")
                    if balayage {
                        let connus = Set(props + codesNikon)
                        self.lireReglages(Array(0x5000...0x50FF).map(UInt16.init).filter { !connus.contains($0) }
                                          + Array(0xD000...0xD2FF).map(UInt16.init).filter { !connus.contains($0) }, "caché ?")
                    }
                    self.file += avant
                } }
            }
            if self.ops.contains(0x90C5) {
                // libgphoto2 l'envoie sans paramètre (ptp.c, ptp_nikon_curve_download) ; ptp.h annonce « 1 param » : on essaie les deux
                for params: [UInt32] in [[], [0]] {
                    self.file.append { self.envoyer(0x90C5, params) { v, rc in
                        let nom = "courbe_90c5_\(params.isEmpty ? "sans" : "p0").bin"
                        if rc == 0x2001, !v.isEmpty { try? v.write(to: sortie.appendingPathComponent(nom)) }
                        self.note("CurveDownload 0x90C5 \(params) : \(rc == 0x2001 ? "\(v.count) octets → \(nom) | \(hexa(v, 64))" : String(format: "réponse 0x%04x", rc))")
                    } }
                }
            } else { self.note("CurveDownload 0x90C5 non annoncée") }
            self.note("CurveUpload 0x90C6 annoncée : \(self.ops.contains(0x90C6) ? "OUI" : "non") (non utilisée)")
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

let sonde = Sonde()
sonde.demarrer()
let limite = Date().addingTimeInterval(300)
let limiteRecherche = Date().addingTimeInterval(20)
while !sonde.fini && Date() < limite && (sonde.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if sonde.boitier == nil { print("Aucun D200 trouvé : allumé (appui à mi-course s'il est en veille), câble USB branché, mode PTP ? Fermer Photos et Transfert d'images.") }
else if !sonde.fini { print("Pas de réponse complète du boîtier dans les 300 s."); sonde.terminer() }
