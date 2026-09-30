// Commandes SCSI Pentax du 645D en mode MSC (menu R2 « USB Connection » = MSC), sans rien installer : le framework IOUSBHost
// de macOS capture le périphérique (il faut être root : « If the caller has root privelages the entitlement and authorization
// is not needed », IOUSBHostDefinitions.h) et l'outil parle lui-même le Bulk-Only Transport (CBW, données, CSW).
//   sudo 645d_scsi lire                       INQUIRY, [00 04] identité, [01 01] version, [00 01] état court, [00 08] état complet
//   sudo 645d_scsi lire-reglages              en plus : [18 00] bloc des réglages (58 mots : balance, Kelvin, Custom Image)
// Protocole : pkTriggerCord, pentax_scsi_protocol.md (CDB de 8 octets, opcode 0xF0 ; 0x4F arguments, 0x24 commande, 0x26 état,
// 0x49 lecture du résultat). Le 645D est grand-boutiste : arguments et résultats en big-endian (recherche/645d-firmware-usb.md).
// Lecture seulement : aucune commande qui change un réglage n'est envoyée (liste `permises`) ; seul [00 00] (mode connecté,
// 1 puis 0, comme pkTriggerCord à chaque session) est permis, et seulement si l'identité est refusée sans lui.
// Les cartes sont démontées avant la capture ; à la fin, `destroy` rend le périphérique et macOS les remonte.
// Lancement : 645d_scsi.sh (fenêtre d'autorisation de macOS, pas de saisie dans le terminal).
// Résultats : 645d/sondes/usb/scsi-<horodatage>/. Analyse : 645d/recherche/645d-usb-et-reglages.md §6.
import Foundation
import IOKit
import IOUSBHost

let a = Array(CommandLine.arguments.dropFirst())
let action = a.first ?? "lire"
let horodatage: String = { let f = DateFormatter(); f.dateFormat = "yyyyMMdd-HHmmss"; return f.string(from: Date()) }()
let sortie = URL(fileURLWithPath: "645d/sondes/usb/scsi-\(horodatage)")
// (groupe, numéro) permis : lectures seulement
let permises: Set<[UInt8]> = [[0x00, 0x00], [0x00, 0x01], [0x00, 0x04], [0x01, 0x01], [0x00, 0x08], [0x18, 0x00]]
var journal: [String] = []
setvbuf(stdout, nil, _IONBF, 0)
func note(_ s: String) {
    print(s); journal.append(s)
    try? journal.joined(separator: "\n").write(toFile: "/private/tmp/645d_scsi-journal.txt", atomically: true, encoding: .utf8)
    try? FileManager.default.createDirectory(at: sortie, withIntermediateDirectories: true)
    try? journal.joined(separator: "\n").write(to: sortie.appendingPathComponent("journal.txt"), atomically: true, encoding: .utf8)
}
func hexa(_ d: Data, _ n: Int = 64) -> String { d.prefix(n).map { String(format: "%02x", $0) }.joined(separator: " ") + (d.count > n ? " …" : "") }
func be32(_ d: Data, _ i: Int) -> UInt32 { (0..<4).reduce(0) { $0 << 8 | UInt32(d[d.startIndex + i + $1]) } }
func le(_ v: UInt32) -> [UInt8] { [UInt8(v & 0xFF), UInt8(v >> 8 & 0xFF), UInt8(v >> 16 & 0xFF), UInt8(v >> 24)] }

guard getuid() == 0 else { print("À lancer en root (sudo ou fenêtre d'autorisation de macOS) : la capture USB l'exige."); exit(2) }

// 1. le 645D en MSC (vendeur 0x25FB, produit 0xF0)
let correspondance = IOServiceMatching("IOUSBHostDevice") as NSMutableDictionary
correspondance["idVendor"] = 0x25FB
correspondance["idProduct"] = 0xF0
let service = IOServiceGetMatchingService(kIOMainPortDefault, correspondance)
guard service != 0 else { print("Aucun 645D en MSC (produit 0xF0) : menu R2 USB Connection = MSC, boîtier allumé et branché."); exit(1) }

// 2. démonter ses cartes (macOS les remontera à la fin) ; elles se montent quelques secondes après le passage en MSC
func cartes() -> [String] { ((try? FileManager.default.contentsOfDirectory(atPath: "/Volumes")) ?? []).filter { $0.hasPrefix("645D") } }
for _ in 0..<20 where cartes().count < 2 { Thread.sleep(forTimeInterval: 1) }
for v in cartes() {
    let p = Process(); p.executableURL = URL(fileURLWithPath: "/usr/sbin/diskutil"); p.arguments = ["unmount", "/Volumes/\(v)"]
    try? p.run(); p.waitUntilExit()
    note("Carte démontée : /Volumes/\(v) (code \(p.terminationStatus))")
}

// 3. capture du périphérique : macOS retire ses pilotes, y compris celui de l'interface de stockage, qui reste en place
// (IOUSBHostDefinitions.h). Ne pas reconfigurer : cela détruit l'interface et l'ancienne disparaît pendant qu'on l'ouvre
// (plantage d’octobre).
let file = DispatchQueue(label: "645d.usb")
let peripherique: IOUSBHostDevice
do { peripherique = try IOUSBHostDevice(__ioService: service, options: [.deviceCapture], queue: file, interestHandler: { _, _, _ in }) }
catch { note("Capture refusée : \(error)"); exit(1) }
note("Capture faite")
func interfaces() -> [io_service_t] {
    var r: [io_service_t] = [], enfants: io_iterator_t = 0
    IORegistryEntryGetChildIterator(service, kIOServicePlane, &enfants)
    while case let e = IOIteratorNext(enfants), e != 0 { if IOObjectConformsTo(e, "IOUSBHostInterface") != 0 { r.append(e) } else { IOObjectRelease(e) } }
    IOObjectRelease(enfants)
    return r
}
func identifiant(_ e: io_service_t) -> UInt64 { var i: UInt64 = 0; IORegistryEntryGetRegistryEntryID(e, &i); return i }
func pilotes(_ e: io_service_t) -> Int { var it: io_iterator_t = 0, n = 0; IORegistryEntryGetChildIterator(e, kIOServicePlane, &it); while case let c = IOIteratorNext(it), c != 0 { n += 1; IOObjectRelease(c) }; IOObjectRelease(it); return n }
// IOUSBHost plante (NSException) quand macOS refuse l'ouverture d'une interface : son message d'erreur sort vide en root
// (octobre et, « IOServiceOpen failed » dans -[IOUSBHostObject openWithOptions:error:]). On fait donc d'abord
// la même ouverture nous-mêmes (IOServiceOpen, type 0, comme le framework) et on n'appelle le framework que si elle passe.
func registre() {
    let p = Process(), tube = Pipe(); p.executableURL = URL(fileURLWithPath: "/usr/sbin/ioreg"); p.arguments = ["-r", "-c", "IOUSBHostDevice", "-w0", "-t"]
    p.standardOutput = tube; try? p.run()
    let t = String(decoding: tube.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)   // lire avant d'attendre : sinon le tube
    p.waitUntilExit()                                                                           // plein bloque ioreg (octobre)
    var dedans = false
    for l in t.split(separator: "\n") { if l.contains("645D@") { dedans = true } else if l.hasPrefix("+-o") { dedans = false }; if dedans { note("  | " + l) } }
}
func ouvrable(_ e: io_service_t) -> kern_return_t {
    var c: io_connect_t = 0
    let kr = IOServiceOpen(e, mach_task_self_, 0, &c)
    if kr == KERN_SUCCESS { IOServiceClose(c) }
    return kr
}
var interface: IOUSBHostInterface?
func essayer(_ etiquette: String, _ exclus: Set<UInt64> = []) {
    for essai in 0..<20 where interface == nil {
        for e in interfaces() where interface == nil && !exclus.contains(identifiant(e)) {
            if pilotes(e) > 0 && essai < 10 { continue }   // pilote de stockage pas encore parti
            let kr = ouvrable(e)
            if essai % 5 == 0 || kr == KERN_SUCCESS { note("  \(etiquette) essai \(essai + 1) : interface \(identifiant(e)), \(pilotes(e)) enfant(s), IOServiceOpen 0x\(String(UInt32(bitPattern: kr), radix: 16))") }
            guard kr == KERN_SUCCESS else { continue }
            do { interface = try IOUSBHostInterface(__ioService: e, options: [], queue: file, interestHandler: { _, _, _ in }) }
            catch { note("  ouverture IOUSBHost : \(error)") }
        }
        if interface == nil { Thread.sleep(forTimeInterval: 0.5) }
    }
}
registre()
essayer("après capture")
if interface == nil {
    let anciennes = Set(interfaces().map(identifiant))
    note("Voie 2 : reconfiguration 1 sans pilote, puis une interface neuve")
    do { try peripherique.__configure(withValue: 1, matchInterfaces: false) } catch { note("  configuration : \(error)") }
    Thread.sleep(forTimeInterval: 1)
    registre()
    essayer("après reconfiguration", anciennes)
}
guard let interface else { note("Interface de stockage impossible à ouvrir : rien envoyé au boîtier."); registre(); peripherique.destroy(); exit(1) }

// points d'accès bulk : on lit les descripteurs de l'interface
var entree: IOUSBHostPipe?, sortieBulk: IOUSBHostPipe?
let config = interface.configurationDescriptor, desc = interface.interfaceDescriptor
var courant = UnsafePointer<IOUSBDescriptorHeader>(OpaquePointer(desc))
while let e = IOUSBGetNextEndpointDescriptor(config, desc, courant) {
    let adresse = e.pointee.bEndpointAddress, genre = e.pointee.bmAttributes & 0x03
    if genre == 2 {
        if adresse & 0x80 != 0 { entree = try? interface.copyPipe(withAddress: Int(adresse)) } else { sortieBulk = try? interface.copyPipe(withAddress: Int(adresse)) }
    }
    courant = UnsafePointer<IOUSBDescriptorHeader>(OpaquePointer(e))
}
guard let entree, let sortieBulk else { note("Points d'accès bulk introuvables."); interface.destroy(); peripherique.destroy(); exit(1) }
note("645D capturé : interface 0, bulk sortie 0x\(String(sortieBulk.endpointAddress, radix: 16)), entrée 0x\(String(entree.endpointAddress, radix: 16))")

// 4. Bulk-Only Transport
var etiquette: UInt32 = 1
enum Sens { case aucun, lecture(Int), ecriture(Data) }
func transfert(_ cdb: [UInt8], _ sens: Sens) -> (Data, UInt8)? {
    etiquette += 1
    var cbw = Data(le(0x43425355) + le(etiquette))
    switch sens {
    case .aucun: cbw += le(0) + [0x00]
    case .lecture(let n): cbw += le(UInt32(n)) + [0x80]
    case .ecriture(let d): cbw += le(UInt32(d.count)) + [0x00]
    }
    cbw += [0x00, UInt8(cdb.count)] + cdb + [UInt8](repeating: 0, count: 16 - cdb.count)
    do { try sortieBulk.__sendIORequest(with: NSMutableData(data: cbw), bytesTransferred: nil, completionTimeout: 5) }
    catch { note("  CBW \(hexa(Data(cdb))) : \(error)"); return nil }
    // une commande refusée peut bloquer (STALL) la phase de données : on débloque et on lit quand même le CSW
    var recu = Data()
    switch sens {
    case .aucun: break
    case .lecture(let n):
        let tampon = NSMutableData(length: n)!; var nb = 0
        do { try entree.__sendIORequest(with: tampon, bytesTransferred: &nb, completionTimeout: 10); recu = Data(tampon.prefix(nb)) }
        catch { note("  données \(hexa(Data(cdb))) : \(error)"); try? entree.clearStall() }
    case .ecriture(let d):
        do { try sortieBulk.__sendIORequest(with: NSMutableData(data: d), bytesTransferred: nil, completionTimeout: 10) }
        catch { note("  données \(hexa(Data(cdb))) : \(error)"); try? sortieBulk.clearStall() }
    }
    for essai in 0..<2 {
        let csw = NSMutableData(length: 13)!; var nb = 0
        do { try entree.__sendIORequest(with: csw, bytesTransferred: &nb, completionTimeout: 10) }
        catch { note("  CSW \(hexa(Data(cdb))) : \(error)"); try? entree.clearStall(); if essai == 0 { continue } else { return nil } }
        let c = Data(csw)
        guard nb == 13, c.prefix(4) == Data(le(0x53425355)) else { note("  CSW invalide : \(hexa(c))"); return nil }
        return (recu, c[12])
    }
    return nil
}

// 5. commandes Pentax
func executer(_ groupe: UInt8, _ numero: UInt8, _ args: [UInt32] = []) -> (UInt8, Data)? {
    guard permises.contains([groupe, numero]) else { note("  [\(String(format: "%02X %02X", groupe, numero))] refusé par l'outil (pas une lecture)"); return nil }
    if !args.isEmpty {
        let d = Data(args.flatMap { v in [UInt8(v >> 24), UInt8(v >> 16 & 0xFF), UInt8(v >> 8 & 0xFF), UInt8(v & 0xFF)] })
        guard transfert([0xF0, 0x4F, 0, 0, UInt8(d.count), 0, 0, 0], .ecriture(d))?.1 == 0 else { return nil }
    }
    guard transfert([0xF0, 0x24, groupe, numero, UInt8(4 * args.count), 0, 0, 0], .aucun)?.1 == 0 else { return nil }
    var etat = Data()
    for _ in 0..<100 {
        guard let (d, s) = transfert([0xF0, 0x26, 0, 0, 0, 0, 0, 0], .lecture(8)), s == 0, d.count == 8 else { return nil }
        etat = d
        if d[6] == 0x01 || d[7] & 0x80 != 0 { break }   // octet 6 = 1 : résultat prêt (pkTriggerCord get_result)
        Thread.sleep(forTimeInterval: 0.05)
    }
    guard etat.count == 8 else { return nil }
    let longueur = Int(etat[0]) | Int(etat[1]) << 8 | Int(etat[2]) << 16 | Int(etat[3]) << 24
    var resultat = Data()
    if etat[7] & 0x80 == 0, longueur > 0, longueur < 0x10000 {
        let n = (longueur + 3) & ~3
        if let (d, s) = transfert([0xF0, 0x49, 0, 0, UInt8(n & 0xFF), UInt8(n >> 8), 0, 0], .lecture(n)), s == 0 { resultat = d }
    }
    return (etat[7], resultat)
}
func texteEtat(_ s: UInt8) -> String { [0x00: "OK", 0x01: "OK", 0x81: "non disponible", 0x82: "refusée", 0x83: "paramètre illégal", 0x84: "refusée (état)"][s] ?? String(format: "0x%02x", s) }

// INQUIRY standard
if let (d, s) = transfert([0x12, 0, 0, 0, 36, 0], .lecture(36)) {
    note("INQUIRY : statut \(s) | « \(String(decoding: d.dropFirst(8).prefix(8), as: UTF8.self)) » « \(String(decoding: d.dropFirst(16).prefix(16), as: UTF8.self)) » « \(String(decoding: d.dropFirst(32).prefix(4), as: UTF8.self)) »")
}
var lectures: [(UInt8, UInt8, String)] = [(0x00, 0x04, "identité"), (0x01, 0x01, "version"), (0x00, 0x01, "état court"), (0x00, 0x08, "état complet")]
if action == "lire-reglages" { lectures.append((0x18, 0x00, "bloc des réglages")) }
var connecte = false
if let (st, _) = executer(0x00, 0x04), st & 0x80 != 0 {
    note("[00 04] refusée hors mode connecté (\(texteEtat(st))) : [00 00] 1")
    connecte = executer(0x00, 0x00, [1]) != nil
}
for (g, n, nom) in lectures {
    guard let (s, d) = executer(g, n) else { note("[\(String(format: "%02X %02X", g, n))] \(nom) : pas de réponse, arrêt"); break }
    try? d.write(to: sortie.appendingPathComponent(String(format: "res_%02x%02x.bin", g, n)))
    let mots = stride(from: 0, to: d.count - 3, by: 4).map { be32(d, $0) }
    note("[\(String(format: "%02X %02X", g, n))] \(nom) : \(texteEtat(s)), \(d.count) octets | " + mots.prefix(16).map { String(format: "0x%X", $0) }.joined(separator: " "))
}
if connecte { note("[00 00] 0 : \(executer(0x00, 0x00, [0]).map { texteEtat($0.0) } ?? "pas de réponse")") }
interface.destroy()
peripherique.destroy()
note("Fin : périphérique rendu à macOS (les cartes se remontent seules).")
