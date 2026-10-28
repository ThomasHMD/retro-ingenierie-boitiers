// Séance de test du Pentax 645D par USB (PTP, mode constructeur) : régler le Custom Image, déclencher, rapatrier PEF et JPEG.
// Réglage seulement, comme d750_preparer.swift : aucun octet de firmware, état de départ sauvé avant toute écriture et remis à la fin.
//   swift 645d/outils/645d_seance.swift <dossier> --sauver            relève les 10 réglages des 8 modes Custom Image (avant-reglages.json,
//                                                                jamais écrasé) ; change le mode le temps du relevé, puis le remet
//   swift 645d/outils/645d_seance.swift <dossier> --essai             une vue avec les réglages du moment, rapatriée (aucune écriture)
//   swift 645d/outils/645d_seance.swift <dossier> [--simulation] [--depuis N]   déroule plan.json : chaque vue règle, relit, déclenche, rapatrie
//   swift 645d/outils/645d_seance.swift <dossier> --remettre          remet avant-reglages.json (chaque mode, puis le mode de départ)
//   swift 645d/outils/645d_seance.swift <dossier> --rapatrier K       lecture seule : rapatrie les K derniers fichiers de la carte
// plan.json : {"vues": [{"nom": "mono-d024-0", "reglages": {"D020": 5, "D024": 0}}, …]} ; le mode (D020) s'écrit toujours en premier,
// chaque réglage s'applique au mode courant (firmware 1.33 : un jeu de 10 paramètres par mode, 645d/recherche/645d-firmware-usb.md §5.1).
// Codes : 0x9001 SetPentaxVendorMode (0x0D, 0x12E08, 1 puis 0), 0x1015/0x1016 Get/SetDevicePropValue, 0x9011 déclenchement
// (0 = vue unique, 2 = appui à fond ; gestionnaire 0x10821140 : [10 0C] 0, [10 0D] 0, puis [10 05] avec le 2e paramètre),
// 0x1007/0x1008/0x1009 pour retrouver et rapatrier les fichiers créés. Écritures permises : la liste `ecrivables`, rien d'autre.
// Le PEF suffit : il contient le JPEG pleine taille rendu par le boîtier avec le Custom Image (JpgFromRaw, 7264 × 5440).
// Une vue déclenchée par USB n'est pas écrite sur la carte : le boîtier la garde en mémoire sous un nom provisoire et l'efface
// à la fermeture de la session. Chaque vue est donc rapatriée avant de fermer sa session (23 vues perdues en octobre sans cela).
// Sécurité : à la première commande sans réponse, l'outil n'envoie plus rien. En octobre, deux fois, la première écriture après une
// vue dans la même session a figé l'USB du boîtier (batterie retirée) : chaque vue se fait donc dans une session neuve, ouverte
// une fois l'état D003 immobile. En Monochrome, filtre par D024, pas D021.
// Préconditions : trépied ou appui stable, scène fixe, exposition (mode M) et mise au point (MF) fixes, balance des blancs fixe,
// Photos et Transfert d'images fermés. D750 et D200 peuvent être branchés : filtre « 645D ». Résultats : 645d/recherche/645d-usb-et-reglages.md.
import Foundation
import ImageCaptureCore

let a = Array(CommandLine.arguments.dropFirst())
let options = CommandLine.arguments
let arguments = a.indices.filter { !a[$0].hasPrefix("--") && !($0 > 0 && ["--depuis", "--rapatrier"].contains(a[$0 - 1])) }.map { a[$0] }
guard arguments.count == 1 else { print("swift 645d/outils/645d_seance.swift <dossier> [--sauver|--essai|--remettre|--rapatrier K|--simulation|--depuis N]"); exit(2) }
let dossier = URL(fileURLWithPath: arguments[0])
let images = dossier.appendingPathComponent("images")
let simulation = options.contains("--simulation"), sauver = options.contains("--sauver"), essai = options.contains("--essai"), remettre = options.contains("--remettre")
func valeurOption(_ nom: String) -> Int? { if let i = options.firstIndex(of: nom), i + 1 < options.count { return Int(options[i + 1]) }; return nil }
let depuis = valeurOption("--depuis") ?? 1, rapatrier = valeurOption("--rapatrier")

// réglages d'un mode Custom Image, lus et remis par --sauver / --remettre (D023 et D028 : écriture toujours refusée par le firmware)
let parMode: [UInt16] = [0xD024, 0xD025, 0xD021, 0xD022, 0x5014, 0x5015, 0xD026, 0xD027, 0xD023, 0xD028]
let ecrivables: Set<UInt16> = [0xD020, 0xD021, 0xD022, 0xD024, 0xD025, 0xD026, 0xD027, 0x5014, 0x5015, 0xD023, 0xD028]
let noms: [UInt16: String] = [0xD020: "mode", 0xD021: "saturation", 0xD022: "teinte", 0xD023: "D023", 0xD024: "D024", 0xD025: "D025",
                              0xD026: "D026", 0xD027: "D027", 0xD028: "D028", 0x5014: "contraste", 0x5015: "netteté"]
let modes = ["Naturel", "Lumineux", "Portrait", "Paysage", "Vibrant", "Monochrome", "Atténué", "Inversion film"]   // codes USB 0 à 7 (pkTriggerCord), à confirmer par l'EXIF
let reponses: [UInt16: String] = [0x2001: "OK", 0x2002: "erreur générale", 0x2005: "non pris en charge", 0x2006: "paramètres non pris en charge",
                                  0x200F: "accès refusé", 0x2017: "mode constructeur fermé", 0x2019: "boîtier occupé", 0x201B: "valeur refusée",
                                  0x201C: "valeur hors plage", 0x201D: "paramètre refusé", 0xA001: "Pentax : échec du déclenchement"]
func texte(_ rc: UInt16) -> String { String(format: "0x%04x", rc) + " " + (reponses[rc] ?? "?") }

struct Lecteur {
    let d: Data; var i = 0
    init(_ d: Data) { self.d = d }
    mutating func u8() -> UInt8 { defer { i += 1 }; return i < d.count ? d[d.startIndex + i] : 0 }
    mutating func u16() -> UInt16 { UInt16(u8()) | UInt16(u8()) << 8 }
    mutating func u32() -> UInt32 { UInt32(u16()) | UInt32(u16()) << 16 }
    mutating func tableau32() -> [UInt32] { let n = Int(u32()); return n > 200000 ? [] : (0..<n).map { _ in u32() } }
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

struct Vue: Decodable { let nom: String; let reglages: [String: Int] }
struct Plan: Decodable { let vues: [Vue] }
struct Sauvegarde: Codable { var heure: String; var mode: Int; var modes: [String: [String: Int]] }

final class Seance: NSObject, ICDeviceBrowserDelegate, ICCameraDeviceDelegate {
    let navigateur = ICDeviceBrowser()
    var boitier: ICCameraDevice?
    var fini = false
    var transaction: UInt32 = 1
    var journal: [String] = []
    var connus = Set<UInt32>()
    var premiereOuverture = true
    let ouverture = DispatchSemaphore(value: 0), fermeture = DispatchSemaphore(value: 0)
    var bloque = false   // une commande sans réponse : plus rien n'est envoyé (incident d’octobre, boîtier figé)
    let nomJournal = rapatrier != nil ? "journal-rapatriement.txt" : "journal.txt"
    func note(_ s: String) { print(s); journal.append(s); try? journal.joined(separator: "\n").write(to: dossier.appendingPathComponent(nomJournal), atomically: true, encoding: .utf8) }

    func envoyer(_ code: UInt16, _ params: [UInt32] = [], donnees: Data? = nil, delai: Double = 30) -> (Data, UInt16) {
        guard let b = boitier, !bloque else { return (Data(), 0) }
        if code == 0x1016, let p = params.first, !ecrivables.contains(UInt16(p)) { note("  écriture 0x\(String(p, radix: 16)) refusée par l'outil"); return (Data(), 0) }
        if simulation, [0x1016, 0x9011].contains(code) { return (Data(), 0x2001) }
        for _ in 0..<40 {
            transaction += 1
            let s = DispatchSemaphore(value: 0); var res = (Data(), UInt16(0))
            b.requestSendPTPCommand(commande(code, transaction: transaction, parametres: params), outData: donnees) { d, r, e in
                if let e { self.note("  0x\(String(code, radix: 16)) : erreur \(e.localizedDescription)") } else { res = (sansEntete(d), codeReponse(r)) }
                s.signal()
            }
            if s.wait(timeout: .now() + delai) == .timedOut {
                bloque = true
                note("  0x\(String(code, radix: 16)) : pas de réponse en \(Int(delai)) s : ARRÊT, plus aucune commande (éteindre et rallumer le boîtier)")
                return res
            }
            if res.1 != 0x2019 { return res }
            Thread.sleep(forTimeInterval: 0.25)
        }
        return (Data(), 0x2019)
    }
    func lire(_ code: UInt16) -> Int? {
        let (d, rc) = envoyer(0x1015, [UInt32(code)])
        guard rc == 0x2001, !d.isEmpty else { return nil }
        return (0..<min(4, d.count)).reduce(0) { $0 | Int(d[d.startIndex + $1]) << (8 * $1) }
    }
    // écrit puis relit ; rend vrai si la valeur relue est la bonne
    func regler(_ code: UInt16, _ v: Int, silencieux: Bool = false) -> Bool {
        let avant = lire(code)
        if avant == v { return true }
        let octets = code == 0xD029 || code == 0xD013 ? 4 : 1
        let rc = envoyer(0x1016, [UInt32(code)], donnees: Data((0..<octets).map { UInt8(truncatingIfNeeded: v >> (8 * $0)) }), delai: 15).1
        if bloque { return false }
        let relu = simulation ? v : lire(code)
        if rc != 0x2001 || relu != v {
            note("  \(noms[code] ?? "?") (0x\(String(code, radix: 16, uppercase: true))) = \(v) : \(texte(rc)), relu \(relu.map(String.init) ?? "?")"); return false
        }
        if !silencieux { note("  \(noms[code] ?? "?") : \(avant.map(String.init) ?? "?") → \(v)") }
        return true
    }
    func handles() -> [UInt32]? {
        let (d, rc) = envoyer(0x1007, [0xFFFFFFFF, 0, 0], delai: 60)
        guard rc == 0x2001 else { return nil }
        var l = Lecteur(d); return l.tableau32()
    }
    func rapatrierObjet(_ h: UInt32, prefixe: String) -> String {
        var l = Lecteur(envoyer(0x1008, [h]).0)
        _ = l.u32(); let format = l.u16(); for _ in 0..<23 { _ = l.u16() }
        let nom = l.chaine()
        if format == 0x3001 { return "dossier \(nom)" }
        let (data, rc) = envoyer(0x1009, [h], delai: 240)
        guard rc == 0x2001, !data.isEmpty else { return "\(nom) non rapatrié (\(texte(rc)))" }
        try? data.write(to: images.appendingPathComponent(prefixe + nom))
        return "\(prefixe + nom) \(data.count / 1024) Ko"
    }
    // déclenche (vue unique, appui à fond) et rapatrie les fichiers apparus
    func declencher(_ prefixe: String) -> Bool {
        let rc = envoyer(0x9011, [0, 2, 0], delai: 60).1
        guard rc == 0x2001 else { note("  déclenchement : \(texte(rc))"); return false }
        if simulation { return true }
        // le PEF et le JPEG n'arrivent pas forcément ensemble (D750) : on attend que la liste ne bouge plus pendant 4 s
        let debut = Date(); var nouveaux: [UInt32] = []; var change = Date()
        while Date().timeIntervalSince(debut) < 90 {
            Thread.sleep(forTimeInterval: 0.7)
            guard let hs = handles() else { continue }
            let n = hs.filter { !connus.contains($0) }
            if n.count != nouveaux.count { nouveaux = n; change = Date() }
            if !nouveaux.isEmpty && Date().timeIntervalSince(change) > 4 { break }
        }
        if nouveaux.isEmpty { note("  aucun fichier nouveau sur la carte en 90 s"); return false }
        // une vue prise par USB n'est PAS écrite sur la carte : elle n'existe qu'en mémoire, jusqu'à la fin de la session (octobre)
        for h in nouveaux { connus.insert(h); note("  " + rapatrierObjet(h, prefixe: prefixe)) }
        return lire(0x5001) != nil
    }
    func releverModes() -> Sauvegarde? {
        guard let depart = lire(0xD020) else { note("Mode Custom Image illisible : arrêt."); return nil }
        var s = Sauvegarde(heure: "\(Date())", mode: depart, modes: [:])
        for m in 0..<8 {
            if m != depart && !regler(0xD020, m, silencieux: true) { note("  mode \(m) : impossible à sélectionner"); continue }
            var r: [String: Int] = [:]
            for c in parMode { if let v = lire(c) { r[String(format: "%04X", c)] = v } }
            s.modes["\(m)"] = r
            note("  \(m) \(modes[m]) : " + parMode.map { c in "\(noms[c]!) \(r[String(format: "%04X", c)].map(String.init) ?? "?")" }.joined(separator: ", "))
        }
        _ = regler(0xD020, depart, silencieux: true)
        note("  mode remis : \(depart) \(modes[depart])")
        return s
    }

    func travail() {
        try? FileManager.default.createDirectory(at: images, withIntermediateDirectories: true)
        note("Séance 645D \(Date())" + (simulation ? " (SIMULATION : rien n'est écrit, aucun déclenchement)" : ""))
        guard envoyer(0x9001, [0x0D, 0x12E08, 1]).1 == 0x2001 else { note("Mode constructeur refusé : arrêt."); return }
        defer { if !bloque { note("Mode constructeur refermé : \(texte(envoyer(0x9001, [0x0D, 0x12E08, 0]).1))") } }
        if let b = lire(0x5001) { note("Batterie \(b) %") }
        connus = Set(handles() ?? [])
        note("Fichiers déjà sur la carte : \(connus.count)")

        if let k = rapatrier {
            for h in connus.sorted().suffix(k) { note("  " + rapatrierObjet(h, prefixe: "rapatrie-")) }
            return
        }
        let fichierAvant = dossier.appendingPathComponent("avant-reglages.json")
        if sauver {
            if FileManager.default.fileExists(atPath: fichierAvant.path) { note("avant-reglages.json existe déjà : gardé tel quel (état du premier relevé)."); return }
            note("Relevé des 8 modes :")
            guard let s = releverModes() else { return }
            let enc = JSONEncoder(); enc.outputFormatting = [.prettyPrinted, .sortedKeys]
            if !simulation, let d = try? enc.encode(s) { try? d.write(to: fichierAvant) }
            return
        }
        if remettre {
            guard let d = try? Data(contentsOf: fichierAvant), let s = try? JSONDecoder().decode(Sauvegarde.self, from: d) else { note("avant-reglages.json absent : rien à remettre."); return }
            var ok = true
            for m in 0..<8 {
                guard let r = s.modes["\(m)"] else { continue }
                if !regler(0xD020, m, silencieux: true) { ok = false; continue }
                for c in parMode where c != 0xD023 && c != 0xD028 { if let v = r[String(format: "%04X", c)], !regler(c, v) { ok = false } }
                for c in parMode { if let v = r[String(format: "%04X", c)], lire(c) != v { note("  mode \(m) : \(noms[c]!) relu \(lire(c).map(String.init) ?? "?") au lieu de \(v)"); ok = false } }
            }
            if !regler(0xD020, s.mode, silencieux: true) { ok = false }
            note(ok ? "Réglages de départ remis (8 modes, mode \(s.mode) \(modes[s.mode]))." : "Remise incomplète : voir plus haut.")
            return
        }
        if essai {
            let n = ((try? FileManager.default.contentsOfDirectory(atPath: images.path)) ?? []).count / 2 + 1
            note("Vue d'essai, réglages du moment (mode \(lire(0xD020).map(String.init) ?? "?")) :")
            _ = declencher(String(format: "essai%02d-", n))
            return
        }
        guard FileManager.default.fileExists(atPath: fichierAvant.path) else { note("Lancer d'abord --sauver (état de départ)."); return }
        guard let p = try? JSONDecoder().decode(Plan.self, from: Data(contentsOf: dossier.appendingPathComponent("plan.json"))) else { note("plan.json illisible."); return }
        var premiere = true
        for (i, v) in p.vues.enumerated() where i + 1 >= depuis {
            if !premiere && !nouvelleSession() { note("  arrêt avant la vue \(i + 1) : reprendre avec --depuis \(i + 1)"); return }
            premiere = false
            note(String(format: "Vue %02d/%02d %@", i + 1, p.vues.count, v.nom))
            var ok = true
            if let m = v.reglages["D020"] { ok = regler(0xD020, m) && ok }
            for (k, val) in v.reglages.sorted(by: { $0.key < $1.key }) where k != "D020" {
                guard let c = UInt16(k, radix: 16) else { continue }
                ok = regler(c, val) && ok
            }
            if !ok { note("  réglage refusé : vue faite quand même (l'EXIF dira ce qui a pris)") }
            if bloque { note("  arrêt sur blocage : reprendre avec --depuis \(i + 1) après redémarrage du boîtier"); return }
            if !declencher(String(format: "%02d-%@-", i + 1, v.nom)) { note("  vue manquée : reprendre avec --depuis \(i + 1)"); return }
        }
        note("Plan terminé. Remettre l'état de départ : --remettre")
    }

    func demarrer() {
        navigateur.delegate = self
        navigateur.browsedDeviceTypeMask = ICDeviceTypeMask(rawValue: ICDeviceTypeMask.camera.rawValue | ICDeviceLocationTypeMask.local.rawValue)!
        navigateur.start()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didAdd device: ICDevice, moreComing: Bool) {
        guard boitier == nil, let b = device as? ICCameraDevice, (b.name ?? "").uppercased().contains("645D"), !(b.transportType ?? "").contains("MassStorage") else { return }
        print("Boîtier trouvé : \(b.name ?? "?")")
        boitier = b; b.delegate = self; b.requestOpenSession()
    }
    func deviceBrowser(_ browser: ICDeviceBrowser, didRemove device: ICDevice, moreGoing: Bool) {}
    func device(_ device: ICDevice, didOpenSessionWithError error: Error?) {
        if !premiereOuverture { if let error { note("  session refusée : \(error.localizedDescription)") } else { ouverture.signal() }; return }
        premiereOuverture = false
        if let error { print("Session refusée : \(error.localizedDescription)"); fini = true; return }
        DispatchQueue.global().async { self.travail(); if !self.bloque { self.boitier?.requestCloseSession() }; self.fini = true }
    }
    func device(_ device: ICDevice, didCloseSessionWithError error: Error?) { fermeture.signal() }
    // Après une vue, la première écriture dans la même session est restée sans réponse (octobre et : batterie
    // retirée). Ce qui a marché : fermer la session, en rouvrir une, puis écrire. On attend aussi que l'état D003 ne bouge plus.
    func nouvelleSession() -> Bool {
        guard let b = boitier, !bloque else { return false }
        _ = envoyer(0x9001, [0x0D, 0x12E08, 0])
        b.requestCloseSession()
        if fermeture.wait(timeout: .now() + 15) == .timedOut { note("  fermeture de session sans réponse"); bloque = true; return false }
        Thread.sleep(forTimeInterval: 5)
        b.requestOpenSession()
        if ouverture.wait(timeout: .now() + 20) == .timedOut { note("  ouverture de session sans réponse"); bloque = true; return false }
        guard envoyer(0x9001, [0x0D, 0x12E08, 1]).1 == 0x2001 else { note("  mode constructeur refusé à la réouverture"); return false }
        var precedent: [UInt8] = [], stables = 0
        let debut = Date()
        while Date().timeIntervalSince(debut) < 40 {
            let (d, rc) = envoyer(0x1015, [0xD003])
            guard rc == 0x2001 else { return false }
            // mots 91 à 96 : capteurs (températures, tensions), ils bougent seuls
            let m = [UInt8](d.prefix(4 + 91 * 4)) + [UInt8](d.dropFirst(4 + 97 * 4))
            stables = m == precedent ? stables + 1 : 0
            precedent = m
            if stables >= 2 { break }
            Thread.sleep(forTimeInterval: 1)
        }
        if stables < 2 { note("  état encore en mouvement après 40 s : arrêt prudent"); return false }
        connus = Set(handles() ?? Array(connus))
        return true
    }
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

let seance = Seance()
seance.demarrer()
let limiteRecherche = Date().addingTimeInterval(20)
while !seance.fini && (seance.boitier != nil || Date() < limiteRecherche) { RunLoop.main.run(until: Date().addingTimeInterval(0.2)) }
if seance.boitier == nil { print("Aucun 645D trouvé : allumé (appui à mi-course s'il est en veille), câble USB branché, mode PTP ? Fermer Photos et Transfert d'images.") }
