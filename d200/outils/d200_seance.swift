// Séance de calibration du D200 par USB, une scène par lot, boîtier sur trépied : exécute le plan de d200_seance.py
// (choix d'Optimiser l'image, crans de Personnalisé, courbes perso), une vue par ligne, NEF et JPEG rapatriés.
// But : tout mesurer sans flasher pour fabriquer ensuite les rendus du firmware (d200/recherche/d200-firmware-image.md).
//   python3 d200/outils/d200_seance.py plan <dossier>
//   swift d200/outils/d200_seance.swift <dossier> [--simulation] [--depuis N] [--rapatrier K]
// À faire par Thomas : trépied, scène fixe en lumière du jour, câble USB, Photos et Transfert d'images fermés. Le reste est
// contrôlé ou réglé par l'outil au départ : batterie (30 % au moins), place sur la carte, taille d'image L, qualité
// NEF + JPEG fine (le NEF embarque le JPEG du boîtier en pleine taille), correction d'exposition à 0. Mode d'exposition
// et mise au point peuvent rester tels quels : chaque JPEG se compare à son propre NEF.
// Ce que l'outil écrit : Optimiser l'image (0xD140), Correction des tons (0xD02B), Mode couleur (0xD02C), Saturation
// (0xD142), Teinte (0xD02D) à chaque vue ; Balance des blancs (0x5005) sur Ensoleillé, Qualité (0x5004) sur 6 et
// Correction d'exposition (0x5010) à 0 pour toute la séance. Valeurs de
// départ, avec l'Espace couleur (0xD032), sauvées dans avant.json (jamais écrasé : une reprise remet celles du premier
// lancement), remises à la fin, même après une erreur, puis relues. Courbe perso : CurveUpload 0x90C6 pour les vues qui
// en ont une, relue par CurveDownload 0x90C5 et comparée octet par octet ; celle d'origine est sauvée dans
// avant_courbe.bin (même règle) et renvoyée à la fin. Rien d'autre : ni firmware, ni banque.
// Déclenchement : InitiateCapture 0x100E sur la carte (le D200 n'a pas 0x9207), puis événements Nikon 0x90C7
// (ObjectAdded 0x4002) et DeviceReady 0x90C8, comme d750_seance.swift.
// --simulation : lit tout et sauve avant.json, n'écrit rien et ne déclenche pas.
// --depuis N : reprend à la vue N (après une coupure).
// --rapatrier K : lecture seule, rapatrie parmi les K derniers fichiers de la carte ceux qui manquent dans images/.
// Analyse ensuite : python3 d200/outils/d200_nb.py comparer <dossier> (N&B), python3 d200/outils/d200_simulateur.py valider <NEF>….
import Foundation
import ImageCaptureCore

let arguments: [String] = {
    let a = Array(CommandLine.arguments.dropFirst())
    return a.indices.filter { !a[$0].hasPrefix("--") && !($0 > 0 && ["--depuis", "--rapatrier"].contains(a[$0 - 1])) }.map { a[$0] }
}()
let options = CommandLine.arguments
let simulation = options.contains("--simulation")
let depuis: Int = { if let i = options.firstIndex(of: "--depuis"), i + 1 < options.count { return Int(options[i + 1]) ?? 1 }; return 1 }()
guard arguments.count == 1 else { print("swift d200/outils/d200_seance.swift <dossier> [--simulation] [--depuis N] [--rapatrier K]"); exit(2) }
let dossier = URL(fileURLWithPath: arguments[0])
let images = dossier.appendingPathComponent("images")
let reponses: [UInt16: String] = [0x2001: "OK", 0x2002: "erreur générale", 0x2006: "paramètres non pris en charge",
                                  0x2019: "boîtier occupé", 0x201D: "valeur refusée", 0xA002: "Nikon : OutOfFocus (passer en mise au point manuelle)",
                                  0xA004: "Nikon : InvalidStatus", 0xA00A: "Nikon : NoCardInSlot ?"]

// Optimiser l'image : 0 Normal, 1 Moins net, 2 Saturé, 3 Très saturé, 4 Portrait, 5 Personnalisé, 6 Noir et blanc.
// Personnalisé : tons 1 Normale, 2 Moins contrasté, 3 Plus contrasté ; mode couleur 0 I, 1 II, 2 III ;
// saturation 1 Normale, 2 Modérée, 3 Accentuée ; teinte en degrés. Ordre des menus, calé sur les valeurs d'usine
// (d200/recherche/d200-ptp-usb.md §4). Les modes Auto, qui s'adaptent à la scène, sont laissés de côté.
let OPTIMISER: UInt16 = 0xD140, TONS: UInt16 = 0xD02B, MODE: UInt16 = 0xD02C, SATURATION: UInt16 = 0xD142, TEINTE: UInt16 = 0xD02D
let BALANCE: UInt16 = 0x5005, ESPACE: UInt16 = 0xD032, ENSOLEILLE = 4
let QUALITE: UInt16 = 0x5004, NEF_FINE = 6, CORRECTION: UInt16 = 0x5010, BATTERIE: UInt16 = 0x5001, TAILLE: UInt16 = 0x5003
let PAR_VUE: UInt64 = 30_000_000   // NEF (≈ 16 Mo) + JPEG fine (≈ 5 Mo), avec de la marge
struct Vue: Decodable { let numero: Int; let nom: String; let reglages: [[Int]]; let courbe: String? }
struct Plan: Decodable { let vues: [Vue] }
let plan: [Vue] = {
    guard let p = try? JSONDecoder().decode(Plan.self, from: Data(contentsOf: dossier.appendingPathComponent("plan.json"))) else {
        print("plan.json illisible dans \(dossier.path) : lancer d'abord python3 d200/outils/d200_seance.py plan <dossier>"); exit(2)
    }
    return p.vues
}()
let TAILLE_COURBE = 0x844
let touches: [UInt16] = [TONS, MODE, SATURATION, TEINTE, ESPACE, BALANCE, QUALITE, CORRECTION, OPTIMISER]   // ordre de remise en état
let noms: [UInt16: String] = [OPTIMISER: "Optimiser l'image", TONS: "Correction des tons", MODE: "Mode couleur",
                              SATURATION: "Saturation", TEINTE: "Teinte", BALANCE: "Balance des blancs", ESPACE: "Espace couleur",
                              QUALITE: "Qualité d'image", CORRECTION: "Correction d'exposition"]

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
// types PTP : 1 INT8, 2 UINT8, 3 INT16, 4 UINT16
func encoder(_ v: Int, type: UInt16) -> Data {
    switch type {
    case 1: return Data([UInt8(bitPattern: Int8(v))])
    case 3: return withUnsafeBytes(of: Int16(v).littleEndian) { Data($0) }
    case 4: return withUnsafeBytes(of: UInt16(v).littleEndian) { Data($0) }
    default: return Data([UInt8(v)])
    }
}

final class Seance: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    var vus = Set<UInt32>()
    var fichiersParVue = 2
    var types: [UInt16: UInt16] = [:]

    let nomJournal = options.contains("--rapatrier") ? "journal-rapatriement.txt" : "journal.txt"
    func note(_ s: String) { print(s); journal.append(s); try? journal.joined(separator: "\n").write(to: dossier.appendingPathComponent(nomJournal), atomically: true, encoding: .utf8) }

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
    // valeur courante d'un réglage, lue dans son descripteur : code(2) type(2) accès(1) défaut(n) courant(n)
    func lire(_ code: UInt16) -> Int? {
        let (d, rc) = envoyer(0x1014, [UInt32(code)])
        guard rc == 0x2001, d.count >= 5 else { return nil }
        let t = UInt16(d[d.startIndex + 2]) | UInt16(d[d.startIndex + 3]) << 8
        types[code] = t
        let n = (t == 3 || t == 4) ? 2 : 1
        guard d.count >= 5 + 2 * n else { return nil }
        let o = d.startIndex + 5 + n
        switch t {
        case 1: return Int(Int8(bitPattern: d[o]))
        case 3: return Int(Int16(bitPattern: UInt16(d[o]) | UInt16(d[o + 1]) << 8))
        case 4: return Int(UInt16(d[o]) | UInt16(d[o + 1]) << 8)
        default: return Int(d[o])
        }
    }
    // écrit puis relit
    func regler(_ code: UInt16, _ v: Int, noter: Bool = true) -> Bool {
        let rc = envoyer(0x1016, [UInt32(code)], donnees: encoder(v, type: types[code] ?? 2)).1
        let relu = lire(code)
        if rc != 0x2001 || relu != v { if noter { note("  \(noms[code] ?? "?") = \(v) : \(texte(rc)), relu \(relu.map(String.init) ?? "?")") }; return false }
        return true
    }
    // des réglages liés (mode couleur II ⇔ Adobe RGB) se refusent selon l'ordre : ceux refusés au premier passage
    // sont repris une fois, après les autres
    func reglerTout(_ liste: [(UInt16, Int)]) -> [(UInt16, Int)] {
        let refuses = liste.filter { !regler($0.0, $0.1, noter: false) }
        return refuses.filter { !regler($0.0, $0.1) }
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice else { return }
        // le D750 sera branché en même temps pour sa propre séance : on ne parle qu'au D200
        guard (b.name ?? "").uppercased().contains("D200") else { print("Ignoré : \(b.name ?? "?") (pas un D200)"); return }
        print("Boîtier trouvé : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        DispatchQueue.global().async { self.travail(); self.boitier?.requestCloseSession(); self.fini = true }
    }

    func evenements() -> [(UInt16, UInt32)] {
        let (d, rc) = envoyer(0x90C7, [], delai: 10)
        guard rc == 0x2001 else { return [] }
        var l = Lecteur(d); let n = Int(l.u16())
        return (0..<min(n, 500)).map { _ in (l.u16(), l.u32()) }
    }
    func nomObjet(_ h: UInt32) -> (UInt16, String) {
        var l = Lecteur(envoyer(0x1008, [h]).0)
        _ = l.u32(); let format = l.u16()
        for _ in 0..<23 { _ = l.u16() }   // jusqu'au nom (ObjectInfo, PTP 1.0)
        return (format, l.chaine())
    }

    func travail() {
        try? FileManager.default.createDirectory(at: images, withIntermediateDirectories: true)
        note("Séance \(Date()) : \(plan.count) vues" + (simulation ? " (SIMULATION : rien n'est écrit ni déclenché)" : ""))
        var l = Lecteur(envoyer(0x1001).0)
        _ = l.u16(); _ = l.u32(); _ = l.u16(); _ = l.chaine(); _ = l.u16()
        let ops = Set(l.tableau16()); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16(); _ = l.tableau16()
        _ = l.chaine(); let modele = l.chaine(), version = l.chaine()
        note("Modèle : \(modele) | firmware : \(version)")
        guard modele.contains("D200") else { note("Ce n'est pas un D200 : arrêt."); return }
        let manquantes = [0x100E, 0x90C5, 0x90C6, 0x90C7, 0x90C8, 0x1004, 0x1005, 0x1007, 0x1008, 0x1009, 0x1014, 0x1016].filter { !ops.contains(UInt16($0)) }
        guard manquantes.isEmpty else { note("Commandes non annoncées : \(manquantes.map { String(format: "0x%04X", $0) }) : arrêt."); return }

        if let i = options.firstIndex(of: "--rapatrier"), i + 1 < options.count, let k = Int(options[i + 1]) {
            var lh = Lecteur(envoyer(0x1007, [0xFFFFFFFF, 0, 0]).0)
            let deja = Set(((try? FileManager.default.contentsOfDirectory(atPath: images.path)) ?? []).compactMap { $0.split(separator: "-").last.map(String.init) })
            for h in lh.tableau32().suffix(k) {
                let (format, nom) = nomObjet(h)
                guard format != 0x3001, !nom.isEmpty, !deja.contains(nom) else { continue }
                let (data, rc) = envoyer(0x1009, [h], delai: 120)
                if rc == 0x2001, !data.isEmpty { try? data.write(to: images.appendingPathComponent("rapatrie-" + nom)) }
                note("Rapatrié \(nom) : " + (rc == 0x2001 ? "\(data.count / 1024) Ko" : texte(rc)))
            }
            return
        }

        // état de départ, sauvé au premier lancement et jamais écrasé (reprise après une coupure)
        let fichierAvant = dossier.appendingPathComponent("avant.json")
        var avant: [String: Int] = [:]
        for c in touches {
            guard let v = lire(c) else { note("Lecture de \(noms[c]!) impossible : arrêt."); return }
            avant[String(format: "0x%04X", c)] = v
        }
        if let d = try? Data(contentsOf: fichierAvant), let a = try? JSONDecoder().decode([String: Int].self, from: d), a.count == touches.count {
            avant = a; note("Reprise : réglages de départ relus dans avant.json")
        } else if let d = try? JSONEncoder().encode(avant) { try? d.write(to: fichierAvant) }
        note("Départ : " + touches.map { "\(noms[$0]!) = \(avant[String(format: "0x%04X", $0)]!)" }.joined(separator: ", "))
        // contrôles de départ : batterie, carte, taille d'image
        let batterie = lire(BATTERIE) ?? 0
        var ls = Lecteur(envoyer(0x1004).0); var libre: UInt64 = 0
        for id in ls.tableau32() {
            var l = Lecteur(envoyer(0x1005, [id]).0)
            _ = l.u16(); _ = l.u16(); _ = l.u16(); _ = l.u32(); _ = l.u32()   // types, accès, capacité
            libre += UInt64(l.u32()) | UInt64(l.u32()) << 32
        }
        var lt = Lecteur(envoyer(0x1015, [UInt32(TAILLE)]).0); let taille = lt.chaine()
        let restantes = plan.filter { $0.numero >= depuis }.count
        note("Batterie \(batterie) % ; carte : \(libre / 1_000_000) Mo libres pour \(restantes) vues ; taille d'image \(taille)")
        guard batterie >= 30 else { note("Batterie sous 30 % : la charger avant la séance. Arrêt."); return }
        guard libre >= UInt64(restantes) * PAR_VUE else { note("Pas assez de place sur la carte (\(UInt64(restantes) * PAR_VUE / 1_000_000) Mo nécessaires) : arrêt."); return }
        guard taille.hasPrefix("3872") else { note("Taille d'image \(taille) : la passer en L (3872 × 2592) au menu Prise de vue. Arrêt."); return }
        let fichierCourbe = dossier.appendingPathComponent("avant_courbe.bin")
        let (lue, rcc) = envoyer(0x90C5)
        guard rcc == 0x2001, lue.count == TAILLE_COURBE else { note("Lecture de la courbe perso impossible (\(texte(rcc)), \(lue.count) octets) : arrêt."); return }
        let courbeAvant: Data
        if let d = try? Data(contentsOf: fichierCourbe), d.count == TAILLE_COURBE { courbeAvant = d; note("Reprise : courbe d'origine relue dans avant_courbe.bin") }
        else { courbeAvant = lue; try? lue.write(to: fichierCourbe) }
        note("Courbe perso de départ : " + (courbeAvant[courbeAvant.startIndex] != 0 && courbeAvant[courbeAvant.startIndex + 1] != 0 ? "présente" : "aucune (entête nul)"))
        var blocs: [String: Data] = [:]
        for v in plan {
            for r in v.reglages where r.count != 2 || noms[UInt16(r[0])] == nil { note("Vue \(v.numero) : réglage inconnu \(r) : arrêt."); return }
            guard let c = v.courbe else { continue }
            guard let b = try? Data(contentsOf: dossier.appendingPathComponent(c)), b.count == TAILLE_COURBE, b[0] != 0, b[1] != 0 else {
                note("Vue \(v.numero) : courbe \(c) absente ou invalide (2 116 octets, octets 0 et 1 non nuls) : arrêt."); return }
            blocs[c] = b
        }
        note("Plan contrôlé : \(plan.count) vues, \(blocs.count) courbes")
        if simulation { note("Simulation terminée : tout est lu, rien n'a été écrit."); return }

        defer {
            let rcf = envoyer(0x90C6, donnees: courbeAvant).1
            note("Fin : courbe perso d'origine renvoyée : " + (rcf == 0x2001 && envoyer(0x90C5).0 == courbeAvant ? "vérifié" : "ÉCHEC (\(texte(rcf)))"))
            let echecs = Set(reglerTout(touches.map { ($0, avant[String(format: "0x%04X", $0)]!) }).map { $0.0 })
            for c in touches {
                note("Fin : \(noms[c]!) remis à \(avant[String(format: "0x%04X", c)]!) : " + (echecs.contains(c) ? "ÉCHEC, à remettre au menu" : "vérifié"))
            }
        }
        for (c, v) in [(BALANCE, ENSOLEILLE), (QUALITE, NEF_FINE), (CORRECTION, 0)] where !regler(c, v) {
            note("\(noms[c]!) : réglage de séance refusé : arrêt."); return
        }
        note("Réglé pour la séance : balance Ensoleillé, qualité NEF + JPEG fine, correction d'exposition 0")
        _ = evenements()   // vide la file
        for vue in plan where vue.numero >= depuis {
            if let c = vue.courbe, let b = blocs[c] {
                var rcu: UInt16 = 0
                for _ in 0..<20 { rcu = envoyer(0x90C6, donnees: b).1; if rcu != 0x2019 { break }; Thread.sleep(forTimeInterval: 0.3) }
                guard rcu == 0x2001, envoyer(0x90C5).0 == b else { note("Vue \(vue.numero) \(vue.nom) : envoi de la courbe refusé ou relu différent (\(texte(rcu))) : arrêt."); return }
            }
            if !reglerTout(vue.reglages.map { (UInt16($0[0]), $0[1]) }).isEmpty { note("Vue \(vue.numero) \(vue.nom) : réglage refusé : arrêt."); return }
            guard let fichiers = declencher(), !fichiers.isEmpty else { note("Vue \(vue.numero) \(vue.nom) : aucune image reçue : arrêt."); return }
            for (handle, nomFichier) in fichiers {
                let (data, rco) = envoyer(0x1009, [handle], delai: 120)
                let cible = images.appendingPathComponent(String(format: "%02d-", vue.numero) + vue.nom + "-" + nomFichier)
                if rco == 0x2001, !data.isEmpty { try? data.write(to: cible) }
                note("Vue \(vue.numero) \(vue.nom) : \(nomFichier) " + (rco == 0x2001 ? "\(data.count / 1024) Ko" : "non rapatrié (\(texte(rco))), il reste sur la carte"))
            }
            if vue.numero == depuis, !fichiers.contains(where: { $0.1.uppercased().hasSuffix(".NEF") }) {
                note("Pas de NEF : passer la qualité d'image en NEF + JPEG fine (ou NEF), puis relancer avec --depuis \(vue.numero) : arrêt."); return
            }
        }
        note("Séance terminée.")
    }

    // déclenche sur la carte et renvoie les fichiers créés (handle, nom)
    func declencher() -> [(UInt32, String)]? {
        var rc: UInt16 = 0
        for _ in 0..<50 {
            rc = envoyer(0x100E, [0, 0]).1
            if rc != 0x2019 { break }
            Thread.sleep(forTimeInterval: 0.2)
        }
        guard rc == 0x2001 else { note("  déclenchement : \(texte(rc))"); return nil }
        // le NEF peut suivre le JPEG de plusieurs secondes (D750, octobre 2026) : on attend les deux, sans reprendre un fichier vu
        let debut = Date(); var out: [(UInt32, String)] = []; var pretDepuis: Date?
        while Date().timeIntervalSince(debut) < 60 {
            for (code, h) in evenements() where code == 0x4002 && !vus.contains(h) {
                vus.insert(h)
                let (format, nom) = nomObjet(h)
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
Avant de lancer : trépied, scène fixe en lumière du jour, câble USB, Photos et Transfert d'images fermés.
Batterie, carte, taille, qualité, balance et correction d'exposition sont contrôlées ou réglées par l'outil, puis remises.
""")
let seance = Seance()
seance.demarrer()
let limiteRecherche = Date().addingTimeInterval(20)
while !seance.fini && (seance.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if seance.boitier == nil { print("Aucun D200 trouvé : allumé (appui à mi-course s'il est en veille), câble USB branché ? Fermer Photos et Transfert d'images.") }
else { print("Journal et images dans \(dossier.path)") }
