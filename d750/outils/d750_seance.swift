// Séance de calibration du D750 par USB : pour chaque vue du plan, écrire le Picture Control dans C-9, l'activer,
// déclencher sur la carte, rapatrier le NEF et le JPEG. Le boîtier reste sur trépied, rien d'autre ne bouge.
//   python3 outils/d750_seance.py plan <dossier>       (fabrique plan.json et les blocs)
//   swift outils/d750_seance.swift <dossier> [--simulation] [--depuis N]
// Préconditions (dites par l'outil au démarrage) : trépied, scène fixe, mode M, mise au point manuelle, balance des blancs
// fixe (pas Auto), D-Lighting actif désactivé, NEF + JPEG fine, pas en U1/U2, Photos et Transfert d'images fermés.
// Ce que l'outil écrit dans le boîtier : l'emplacement C-9 (SetPictCtrlData 0x90CD, remplacé à chaque vue) et le Picture
// Control actif (0xD200). À la fin : C-9 remis comme avant (effacé s'il était vide) et 0xD200 remis à sa valeur de départ.
// Rien d'autre : ni firmware, ni autre réglage. Format et preuves : recherche/d750-picture-control-usb.md.
// Déclenchement : InitiateCaptureRecInMedia 0x9207 (0xFFFFFFFF = sans autofocus, 0 = sur la carte), puis DeviceReady 0x90C8
// et les événements Nikon 0x90C7 (ObjectAdded 0x4002), comme libgphoto2 (camlibs/ptp2/library.c, capture Nikon).
// --simulation : lit tout (DeviceInfo, C-9, 0xD200) et contrôle les blocs, n'écrit rien et ne déclenche pas.
// --depuis N : reprend à la vue N (après une coupure).
// --kelvin N : règle la température de couleur (balance des blancs déjà en mode K) pour la séance, remise à la fin.
// --rapatrier K : lecture seule, rapatrie parmi les K derniers fichiers de la carte ceux qui manquent dans images/.
import Foundation
import ImageCaptureCore

let arguments: [String] = {   // sans les options ni leur valeur (--depuis N, --rapatrier K, --kelvin N)
    let a = Array(CommandLine.arguments.dropFirst())
    return a.indices.filter { !a[$0].hasPrefix("--") && !($0 > 0 && ["--depuis", "--rapatrier", "--kelvin"].contains(a[$0 - 1])) }.map { a[$0] }
}()
let options = CommandLine.arguments
let simulation = options.contains("--simulation")
let depuis: Int = { if let i = options.firstIndex(of: "--depuis"), i + 1 < options.count { return Int(options[i + 1]) ?? 1 }; return 1 }()
guard arguments.count == 1 else { print("swift outils/d750_seance.swift <dossier du plan> [--simulation] [--depuis N] [--rapatrier K]"); exit(2) }
let dossier = URL(fileURLWithPath: arguments[0])
let images = dossier.appendingPathComponent("images")
let item: UInt32 = 209   // C-9
let reponses: [UInt16: String] = [0x2001: "OK", 0x2002: "erreur générale", 0x2006: "paramètres non pris en charge",
                                  0x2007: "transfert incomplet", 0x200F: "accès refusé (U1/U2 ?)", 0x2019: "boîtier occupé",
                                  0x201D: "paramètre ou bloc refusé", 0xA001: "Nikon : HardwareError", 0xA002: "Nikon : OutOfFocus",
                                  0xA003: "Nikon : ChangeCameraModeFailed", 0xA004: "Nikon : InvalidStatus", 0xA00A: "Nikon : NoCardInSlot ?"]

struct Vue: Decodable { let numero: Int; let nom: String; let bloc: String; let octets: Int }
struct Plan: Decodable { let emplacement: String; let vues: [Vue] }
let plan: Plan = {
    guard let p = try? JSONDecoder().decode(Plan.self, from: Data(contentsOf: dossier.appendingPathComponent("plan.json"))) else {
        print("plan.json illisible dans \(dossier.path) : lancer d'abord python3 outils/d750_seance.py plan <dossier>"); exit(2)
    }
    return p
}()

func controle(_ b: Data) -> String? {
    let o = { (i: Int) in b[b.startIndex + i] }
    guard b.count == 32 || b.count == 610 else { return "\(b.count) octets : 32 ou 610 attendus" }
    guard (1...7).contains(o(0)), o(1) == (o(0) == 4 ? 1 : 0), o(2) == 1 else { return "base ou drapeaux invalides" }
    guard (3..<23).allSatisfy({ o($0) == 0 || (0x20..<0x7F).contains(o($0)) }), o(22) == 0, o(3) != 0 else { return "nom invalide" }
    guard o(0) == 4 || o(23) == 0 else { return "accentuation rapide interdite en perso" }
    guard o(31) == (b.count == 610 ? 1 : 0), b.count == 32 || (o(32) == 0x49 && o(33) == 0x30) else { return "courbe incohérente" }
    return nil
}
func nomDe(_ v: Data) -> String { v.count >= 23 ? String(decoding: v.subdata(in: (v.startIndex + 3)..<(v.startIndex + 23)).prefix { $0 != 0 }, as: UTF8.self) : "" }
func genre(_ v: Data) -> Int { v.count >= 3 ? Int(v[v.startIndex + 2]) : -1 }
func ecarts(_ a: Data, _ b: Data) -> [Int] {
    guard a.count == b.count else { return [-1] }
    return (0..<a.count).filter { a[a.startIndex + $0] != b[b.startIndex + $0] && !(a.count == 610 && ($0 == 28 || $0 == 29)) }
}
struct Lecteur {
    let d: Data; var i = 0
    init(_ d: Data) { self.d = d }
    mutating func u8() -> UInt8 { defer { i += 1 }; return i < d.count ? d[d.startIndex + i] : 0 }
    mutating func u16() -> UInt16 { UInt16(u8()) | UInt16(u8()) << 8 }
    mutating func u32() -> UInt32 { UInt32(u16()) | UInt32(u16()) << 16 }
    mutating func tableau16() -> [UInt16] { let n = Int(u32()); return n > 2000 ? [] : (0..<n).map { _ in u16() } }
    mutating func tableau32() -> [UInt32] { let n = Int(u32()); return n > 100000 ? [] : (0..<n).map { _ in u32() } }
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
    if p.count >= 12, p[p.startIndex + 4] == 2, Int(p[p.startIndex]) | Int(p[p.startIndex + 1]) << 8 | Int(p[p.startIndex + 2]) << 16 | Int(p[p.startIndex + 3]) << 24 == p.count {
        return p.subdata(in: (p.startIndex + 12)..<p.endIndex)
    }
    return p
}
func codeReponse(_ r: Data) -> UInt16 { r.count >= 8 ? UInt16(r[r.startIndex + 6]) | UInt16(r[r.startIndex + 7]) << 8 : 0 }
func texte(_ rc: UInt16) -> String { String(format: "0x%04x", rc) + " " + (reponses[rc] ?? "?") }
func petit<T: FixedWidthInteger>(_ v: T) -> Data { withUnsafeBytes(of: v.littleEndian) { Data($0) } }

final class Seance: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var pret = false, fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    var vus = Set<UInt32>()          // fichiers déjà rapatriés
    var fichiersParVue = 2           // NEF + JPEG

    // le rapatriement a son propre journal : il ne doit pas écraser celui de la séance
    let nomJournal = options.contains("--rapatrier") ? "journal-rapatriement.txt" : "journal.txt"
    func note(_ s: String) { print(s); journal.append(s); try? journal.joined(separator: "\n").write(to: dossier.appendingPathComponent(nomJournal), atomically: true, encoding: .utf8) }

    // commande synchrone, appelée depuis le fil de travail (jamais depuis le fil principal, qui fait tourner la boucle)
    func envoyer(_ code: UInt16, _ params: [UInt32] = [], donnees: Data? = nil, delai: Double = 60) -> (Data, UInt16) {
        guard let b = boitier else { return (Data(), 0) }
        transaction += 1
        let s = DispatchSemaphore(value: 0); var res = (Data(), UInt16(0))
        b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: donnees) { d, r, e in
            if let e { self.note("  0x\(String(code, radix: 16)) : erreur \(e.localizedDescription)") } else { res = (sansEntete(d), codeReponse(r)) }
            s.signal()
        }
        if s.wait(timeout: .now() + delai) == .timedOut { note("  0x\(String(code, radix: 16)) : pas de réponse en \(Int(delai)) s") }
        return res
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice else { return }
        // un autre boîtier peut être branché en même temps (le D40, octobre 2026) : on ne parle qu'au D750
        guard (b.name ?? "").uppercased().contains("D750") else { print("Ignoré : \(b.name ?? "?") (pas un D750)"); return }
        print("Boîtier trouvé : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        pret = true
        DispatchQueue.global().async { self.travail(); self.boitier?.requestCloseSession(); self.fini = true }
    }

    // événements Nikon en attente (0x90C7) : liste de (code, paramètre)
    func evenements() -> [(UInt16, UInt32)] {
        let (d, rc) = envoyer(0x90C7, [], delai: 10)
        guard rc == 0x2001 else { return [] }
        var l = Lecteur(d); let n = Int(l.u16())
        return (0..<min(n, 500)).map { _ in (l.u16(), l.u32()) }
    }

    func travail() {
        try? FileManager.default.createDirectory(at: images, withIntermediateDirectories: true)
        note("Séance \(Date()) : \(plan.vues.count) vues, emplacement C-9" + (simulation ? " (SIMULATION : rien n'est écrit ni déclenché)" : ""))
        var l = Lecteur(envoyer(0x1001).0)
        _ = l.u16(); _ = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
        let ops = Set(l.tableau16()); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16()
        _ = l.chaine(); let modele = l.chaine(), version = l.chaine()
        note("Modèle : \(modele) | firmware : \(version)")
        guard modele.contains("D750") else { note("Ce n'est pas un D750 : arrêt."); return }
        let manquantes = [0x90CC, 0x90CD, 0x90CE, 0x9207, 0x90C7, 0x90C8, 0x1008, 0x1009, 0x1014, 0x1015, 0x1016].filter { !ops.contains(UInt16($0)) }
        guard manquantes.isEmpty else { note("Commandes non annoncées : \(manquantes.map { String(format: "0x%04X", $0) }) : arrêt."); return }

        if let i = options.firstIndex(of: "--rapatrier"), i + 1 < options.count, let k = Int(options[i + 1]) {
            // lecture seule : les k derniers fichiers de la carte qui manquent dans images/ (fin de séance coupée, dernière vue)
            var lh = Lecteur(envoyer(0x1007, [0xFFFFFFFF, 0, 0]).0)
            let tous = lh.tableau32()
            let deja = Set(((try? FileManager.default.contentsOfDirectory(atPath: images.path)) ?? []).compactMap { $0.split(separator: "-").last.map(String.init) })
            for h in tous.suffix(k) {
                var l = Lecteur(envoyer(0x1008, [h]).0)
                _ = l.u32(); let format = l.u16()
                for _ in 0..<23 { _ = l.u16() }
                let nom = l.chaine()
                guard format != 0x3001, !nom.isEmpty, !deja.contains(nom) else { continue }
                let (data, rc) = envoyer(0x1009, [h], delai: 120)
                if rc == 0x2001, !data.isEmpty { try? data.write(to: images.appendingPathComponent("rapatrie-" + nom)) }
                note("Rapatrié \(nom) : " + (rc == 0x2001 ? "\(data.count / 1024) Ko" : texte(rc)))
            }
            return
        }
        // état de départ : Picture Control actif et C-9
        let desc = envoyer(0x1014, [0xD200]).0
        let type = desc.count >= 4 ? UInt16(desc[desc.startIndex + 2]) | UInt16(desc[desc.startIndex + 3]) << 8 : 4
        let (v, rcv) = envoyer(0x1015, [0xD200])
        guard rcv == 0x2001, !v.isEmpty else { note("Lecture du Picture Control actif impossible (\(texte(rcv))) : arrêt."); return }
        let actif = type == 2 ? UInt32(v[v.startIndex]) : UInt32(v[v.startIndex]) | UInt32(v.count > 1 ? v[v.startIndex + 1] : 0) << 8
        let encode = { (n: UInt32) -> Data in type == 2 ? Data([UInt8(n & 0xFF)]) : petit(UInt16(n)) }
        let lu = envoyer(0x90CC, [item, 0]).0
        // reprise après une coupure : C-9 peut contenir une vue de séance ; on remet à la fin le contenu d'origine,
        // sauvé au premier lancement dans ce dossier, jamais écrasé ensuite
        let fichierAvant = dossier.appendingPathComponent("avant_c9.bin")
        let avant: Data
        if let d = try? Data(contentsOf: fichierAvant), !d.isEmpty { avant = d; note("Reprise : contenu d'origine de C-9 relu dans avant_c9.bin (« \(nomDe(d)) »)") }
        else { avant = lu; try? lu.write(to: fichierAvant) }
        note("Départ : Picture Control actif = \(actif) ; C-9 = " + (genre(lu) == 2 ? "vide" : "« \(nomDe(lu)) »"))
        let nomsDuPlan = Set(plan.vues.map { $0.nom })
        guard genre(lu) == 2 || nomsDuPlan.contains(nomDe(lu)) || options.contains("--remplacer") else {
            note("C-9 contient « \(nomDe(lu)) », qui n'est pas une vue de séance : arrêt (ajouter --remplacer pour l'utiliser quand même ; son contenu est sauvé dans avant_c9.bin)."); return
        }
        var blocs: [Int: Data] = [:]
        for vue in plan.vues {
            guard let b = try? Data(contentsOf: dossier.appendingPathComponent(vue.bloc)) else { note("Bloc \(vue.bloc) illisible : arrêt."); return }
            if let p = controle(b) { note("Vue \(vue.numero) (\(vue.nom)) : bloc refusé avant tout envoi : \(p). Arrêt."); return }
            blocs[vue.numero] = b
        }
        note("Blocs contrôlés : \(blocs.count)")
        // --kelvin N : température de couleur (0xD01E, UINT16) réglée pour la séance, remise à sa valeur de départ à la fin ;
        // seulement si la balance des blancs est déjà en mode K (0x5005 = 0x8012)
        var kelvinDepart: UInt16? = nil
        if let i = options.firstIndex(of: "--kelvin"), i + 1 < options.count, let k = UInt16(options[i + 1]) {
            let wb = envoyer(0x1015, [0x5005]).0, t = envoyer(0x1015, [0xD01E]).0
            guard wb.count >= 2, UInt16(wb[wb.startIndex]) | UInt16(wb[wb.startIndex + 1]) << 8 == 0x8012, t.count >= 2 else {
                note("Balance des blancs pas en mode K (choisir K sur le boîtier) : arrêt."); return }
            kelvinDepart = UInt16(t[t.startIndex]) | UInt16(t[t.startIndex + 1]) << 8
            note("Température : \(kelvinDepart!) K au départ, \(k) K pour la séance" + (simulation ? " (simulation : non réglée)" : ""))
            if !simulation {
                let rc = envoyer(0x1016, [0xD01E], donnees: petit(k)).1
                guard rc == 0x2001 else { note("Réglage de la température refusé (\(texte(rc))) : arrêt."); return }
            }
        }
        if simulation { note("Simulation terminée : tout est prêt, rien n'a été écrit."); return }

        defer {
            // remise en état, même après une erreur
            if genre(avant) == 2 { note("Fin : effacement de C-9 : \(texte(envoyer(0x90CE, [item]).1))") }
            else if genre(avant) == 1, controle(avant) == nil { note("Fin : C-9 remis comme avant : \(texte(envoyer(0x90CD, [item, 0], donnees: avant).1))") }
            note("Fin : Picture Control actif remis à \(actif) : \(texte(envoyer(0x1016, [0xD200], donnees: encode(actif)).1))")
            if let k = kelvinDepart { note("Fin : température remise à \(k) K : \(texte(envoyer(0x1016, [0xD01E], donnees: petit(k)).1))") }
        }
        _ = evenements()   // vide la file
        for vue in plan.vues where vue.numero >= depuis {
            let b = blocs[vue.numero]!
            let rc = envoyer(0x90CD, [item, 0], donnees: b).1
            guard rc == 0x2001 else { note("Vue \(vue.numero) \(vue.nom) : écriture refusée (\(texte(rc))) : arrêt."); return }
            let e = ecarts(b, envoyer(0x90CC, [item, 0]).0)
            guard e.isEmpty else { note("Vue \(vue.numero) \(vue.nom) : relecture différente (octets \(e)) : arrêt."); return }
            let rca = envoyer(0x1016, [0xD200], donnees: encode(item)).1
            guard rca == 0x2001 else { note("Vue \(vue.numero) : activation de C-9 refusée (\(texte(rca))) : arrêt."); return }
            guard let fichiers = declencher(), !fichiers.isEmpty else { note("Vue \(vue.numero) \(vue.nom) : aucune image reçue : arrêt."); return }
            for (handle, nomFichier) in fichiers {
                let (data, rco) = envoyer(0x1009, [handle], delai: 120)
                let cible = images.appendingPathComponent(String(format: "%02d-", vue.numero) + vue.nom.replacingOccurrences(of: " ", with: "_") + "-" + nomFichier)
                if rco == 0x2001, !data.isEmpty { try? data.write(to: cible) }
                note("Vue \(vue.numero) \(vue.nom) : \(nomFichier) " + (rco == 0x2001 ? "\(data.count / 1024) Ko" : "non rapatrié (\(texte(rco))), il reste sur la carte"))
            }
        }
        note("Séance terminée.")
    }

    // déclenche sur la carte et renvoie les fichiers créés (handle, nom)
    func declencher() -> [(UInt32, String)]? {
        var rc: UInt16 = 0
        for _ in 0..<50 {
            rc = envoyer(0x9207, [0xFFFFFFFF, 0]).1
            if rc == 0x2006 { rc = envoyer(0x9207, [0xFFFFFFFF]).1 }
            if rc != 0x2019 { break }
            Thread.sleep(forTimeInterval: 0.2)
        }
        guard rc == 0x2001 else { note("  déclenchement : \(texte(rc))"); return nil }
        // le JPEG et le NEF d'une vue n'arrivent pas ensemble (le NEF peut suivre de plusieurs secondes, séance d’octobre 2026) :
        // on attend les deux fichiers de la vue, et un fichier déjà rapatrié n'est jamais repris
        let debut = Date(); var out: [(UInt32, String)] = []; var pretDepuis: Date?
        while Date().timeIntervalSince(debut) < 60 {
            for (code, h) in evenements() where code == 0x4002 && !vus.contains(h) {
                vus.insert(h)
                var l = Lecteur(envoyer(0x1008, [h]).0)
                _ = l.u32(); let format = l.u16()
                for _ in 0..<23 { _ = l.u16() }   // jusqu'au nom : 2+4+2+4+4+4+4+4+4+4+2+4+4 = 46 octets après le format (ObjectInfo, PTP 1.0)
                let nom = l.chaine()
                if format != 0x3001 { out.append((h, nom.isEmpty ? String(format: "objet-%08x", h) : nom)) }
            }
            if pretDepuis == nil, envoyer(0x90C8, [], delai: 10).1 == 0x2001 { pretDepuis = Date() }
            if let t = pretDepuis, out.count >= fichiersParVue || Date().timeIntervalSince(t) > 20 { break }
            Thread.sleep(forTimeInterval: 0.3)
        }
        if !out.isEmpty { fichiersParVue = max(fichiersParVue, out.count) }
        return out
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

print("""
Avant de lancer : trépied, scène fixe et variée (neutres, ciel, peau, rouge, jaune, vert), mode M, mise au point manuelle,
balance des blancs fixe (pas Auto), D-Lighting actif désactivé, NEF + JPEG fine, pas en U1/U2.
""")
let seance = Seance()
seance.demarrer()
let limiteRecherche = Date().addingTimeInterval(20)
while !seance.fini && (seance.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if seance.boitier == nil { print("Aucun boîtier trouvé : allumé, câble USB branché ? Fermer Photos et Transfert d'images s'ils s'ouvrent.") }
else { print("Journal et images dans \(dossier.path)") }
