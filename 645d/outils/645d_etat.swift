// Relevé de l'état du Pentax 645D par USB (PTP, mode constructeur), pour la correspondance « réglage au menu ↔ valeur USB ».
//   swift 645d/outils/645d_etat.swift <étiquette>              un relevé, comparé au précédent (etats/<n>-<étiquette>.json)
//   swift 645d/outils/645d_etat.swift --suivre [secondes]      relève toutes les 2 s et note chaque changement (Thomas règle au menu)
// Lecture seule : GetDeviceInfo (0x1001), GetDevicePropValue (0x1015), GetAllConditions (0x900F), et 0x9001 SetPentaxVendorMode
// (mode de connexion, aucun réglage), ouvert puis refermé à chaque relevé. Rien n'est écrit dans le boîtier.
// Lus : les réglages Custom Image et voisins (5004, 5014, 5015, D013, D020 à D029, D032), le tableau d'état D003 (109 mots,
// commande interne [00 08]) et GetAllConditions (le même, plus deux mots). Les réglages standard en lecture seule (5005, 5007…)
// rendent leur propre code au lieu d'une valeur (sonde d’octobre 2026) : leur état est dans D003.
// Résultats : 645d/sondes/usb/etats/. Analyse : 645d/recherche/645d-usb-et-reglages.md. D750 et D200 peuvent être branchés : filtre « 645D ».
import Foundation
import ImageCaptureCore

let a = Array(CommandLine.arguments.dropFirst())
let suivre = a.contains("--suivre")
let duree: Double = { if let i = a.firstIndex(of: "--suivre"), i + 1 < a.count, let s = Double(a[i + 1]) { return s }; return 600 }()
let etiquette = a.filter { !$0.hasPrefix("--") && Double($0) == nil }.first ?? "releve"
guard suivre || !a.filter({ !$0.hasPrefix("--") }).isEmpty else { print("swift 645d/outils/645d_etat.swift <étiquette> | --suivre [secondes]"); exit(2) }
let dossier = URL(fileURLWithPath: "645d/sondes/usb/etats")
let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let heure: () -> String = { let f = DateFormatter(); f.dateFormat = "HH:mm:ss"; return f.string(from: Date()) }

// code : (nom, octets)
let reglages: [(UInt16, String, Int)] = [(0x5004, "qualité JPEG", 1), (0x5014, "contraste", 1), (0x5015, "netteté", 1),
    (0xD013, "entraînement", 4), (0xD020, "mode Custom Image", 1), (0xD021, "saturation", 1), (0xD022, "teinte", 1),
    (0xD023, "D023", 1), (0xD024, "D024", 1), (0xD025, "D025", 1), (0xD026, "D026 netteté fine ?", 1), (0xD027, "D027", 1),
    (0xD028, "D028", 1), (0xD029, "espace couleur", 4)]

func commande(_ code: UInt16, transaction: UInt32, parametres: [UInt32] = []) -> Data {
    var d = Data()
    func ajoute<T: FixedWidthInteger>(_ v: T) { withUnsafeBytes(of: v.littleEndian) { d.append(contentsOf: $0) } }
    ajoute(UInt32(12 + 4 * parametres.count)); ajoute(UInt16(1)); ajoute(code); ajoute(transaction)
    parametres.forEach { ajoute($0) }
    return d
}
func sansEntete(_ p: Data) -> Data {
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 | Int(p[p.startIndex + 3]) << 24 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func mots(_ d: Data, depuis debut: Int = 0) -> [Int] {
    stride(from: debut, to: d.count - 3, by: 4).map { i in Int(d[d.startIndex + i]) | Int(d[d.startIndex + i + 1]) << 8 | Int(d[d.startIndex + i + 2]) << 16 | Int(d[d.startIndex + i + 3]) << 24 }
}
func entier(_ d: Data, _ n: Int) -> Int { (0..<min(n, d.count)).reduce(0) { $0 | Int(d[d.startIndex + $1]) << (8 * $1) } }

struct Releve: Codable { var heure: String; var etiquette: String; var reglages: [String: Int]; var d003: [Int]; var c900f: [Int] }

final class Etat: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    let fichierJournal = dossier.appendingPathComponent(suivre ? "suivi-\(horodatage).txt" : "journal.txt")
    func note(_ s: String) {
        print(s); journal.append(s)
        let ancien = suivre ? "" : ((try? String(contentsOf: fichierJournal, encoding: .utf8)) ?? "")
        try? (ancien + (suivre ? journal.joined(separator: "\n") : s) + "\n").write(to: fichierJournal, atomically: true, encoding: .utf8)
    }

    func envoyer(_ code: UInt16, _ params: [UInt32] = [], delai: Double = 20) -> (Data, UInt16) {
        guard let b = boitier, [0x1001, 0x1015, 0x9001, 0x900F].contains(code) else { return (Data(), 0) }   // lectures seulement
        transaction += 1
        let s = DispatchSemaphore(value: 0); var res = (Data(), UInt16(0))
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: nil) { d, r, e in
            if e == nil { res = (sansEntete(d), codeReponse(r)) }
            s.signal()
        }
        _ = s.wait(timeout: .now() + delai)
        return res
    }
    func relever() -> Releve? {
        guard envoyer(0x9001, [0x0D, 0x12E08, 1]).1 == 0x2001 else { return nil }
        defer { _ = envoyer(0x9001, [0x0D, 0x12E08, 0]) }
        var r = Releve(heure: heure(), etiquette: etiquette, reglages: [:], d003: [], c900f: [])
        for (code, _, n) in reglages {
            let (d, rc) = envoyer(0x1015, [UInt32(code)])
            if rc == 0x2001 { r.reglages[String(format: "%04X", code)] = entier(d, n) }
        }
        let (d3, rc3) = envoyer(0x1015, [0xD003]); if rc3 == 0x2001 { r.d003 = mots(d3, depuis: 4) }
        let (c9, rc9) = envoyer(0x900F); if rc9 == 0x2001 { r.c900f = mots(c9, depuis: 4) }
        return r
    }
    func differences(_ avant: Releve, _ apres: Releve) -> [String] {
        var out: [String] = []
        for (code, nom, _) in reglages {
            let k = String(format: "%04X", code)
            if avant.reglages[k] != apres.reglages[k] { out.append("\(nom) (0x\(k)) : \(avant.reglages[k].map(String.init) ?? "?") → \(apres.reglages[k].map(String.init) ?? "?")") }
        }
        for i in 0..<max(avant.d003.count, apres.d003.count) where (i < avant.d003.count ? avant.d003[i] : nil) != (i < apres.d003.count ? apres.d003[i] : nil) {
            out.append("D003[\(i)] : \(i < avant.d003.count ? String(avant.d003[i]) : "?") → \(i < apres.d003.count ? String(apres.d003[i]) : "?")")
        }
        for i in 0..<max(avant.c900f.count, apres.c900f.count) where (i < avant.c900f.count ? avant.c900f[i] : nil) != (i < apres.c900f.count ? apres.c900f[i] : nil) {
            if i < apres.d003.count, i < avant.d003.count, avant.d003[i] != apres.d003[i] { continue }   // déjà dit par D003
            out.append("900F[\(i)] : \(i < avant.c900f.count ? String(avant.c900f[i]) : "?") → \(i < apres.c900f.count ? String(apres.c900f[i]) : "?")")
        }
        return out
    }

    func travail() {
        try? FileManager.default.createDirectory(at: dossier, withIntermediateDirectories: true)
        if !suivre {
            guard let r = relever() else { note("\(heure()) mode constructeur refusé : arrêt."); return }
            let existants = ((try? FileManager.default.contentsOfDirectory(atPath: dossier.path)) ?? []).filter { $0.hasSuffix(".json") }.sorted()
            let n = existants.count + 1
            let nom = String(format: "%03d-", n) + etiquette.replacingOccurrences(of: "/", with: "-") + ".json"
            let enc = JSONEncoder(); enc.outputFormatting = [.sortedKeys]
            if let d = try? enc.encode(r) { try? d.write(to: dossier.appendingPathComponent(nom)) }
            note("\(r.heure) relevé \(nom) : " + reglages.map { "\(String(format: "%04X", $0.0))=\(r.reglages[String(format: "%04X", $0.0)].map(String.init) ?? "?")" }.joined(separator: " "))
            if let precedent = existants.last, let d = try? Data(contentsOf: dossier.appendingPathComponent(precedent)), let p = try? JSONDecoder().decode(Releve.self, from: d) {
                let diff = differences(p, r)
                note("  comparé à \(precedent) : " + (diff.isEmpty ? "aucun changement" : ""))
                diff.forEach { note("    " + $0) }
            }
            return
        }
        note("\(heure()) suivi pendant \(Int(duree)) s : Thomas règle au menu, chaque changement est noté.")
        var dernier = relever()
        if let r = dernier { note("\(r.heure) départ : " + reglages.map { "\(String(format: "%04X", $0.0))=\(r.reglages[String(format: "%04X", $0.0)].map(String.init) ?? "?")" }.joined(separator: " ")) }
        let debut = Date(); var muets = 0
        while Date().timeIntervalSince(debut) < duree {
            Thread.sleep(forTimeInterval: 2)
            guard let r = relever() else { muets += 1; if muets == 1 { note("\(heure()) pas de réponse (menu ouvert ou veille ?)") }; continue }
            if muets > 0 { note("\(r.heure) le boîtier répond de nouveau"); muets = 0 }
            if let p = dernier { let diff = differences(p, r); if !diff.isEmpty { note("\(r.heure) changement :"); diff.forEach { note("    " + $0) } } }
            dernier = r
        }
        if let r = dernier, let d = try? JSONEncoder().encode(r) { try? d.write(to: dossier.appendingPathComponent("suivi-\(horodatage)-fin.json")) }
        note("\(heure()) fin du suivi.")
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").uppercased().contains("645D"), !(b.transportType ?? "").contains("MassStorage") else { return }
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        DispatchQueue.global().async { self.travail(); self.boitier?.requestCloseSession(); self.fini = true }
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

let etat = Etat()
etat.demarrer()
let limiteRecherche = Date().addingTimeInterval(20)
while !etat.fini && (etat.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if etat.boitier == nil { print("Aucun 645D trouvé : allumé (appui à mi-course s'il est en veille), câble USB branché, mode PTP ? Fermer Photos et Transfert d'images.") }
