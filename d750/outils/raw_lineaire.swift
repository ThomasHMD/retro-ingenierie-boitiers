// Développe un RAW (RAF, NEF…) avec le décodeur de macOS, sans courbe ni look :
// sortie TIFF 16 bits en sRGB linéaire, réduite, pixels dans le sens du capteur.
// Sert de référence « scène » pour mesurer un rendu (Classic Chrome…) contre son RAW.
//
//   swiftc -O outils/raw_lineaire.swift -o <dossier jetable>/raw_lineaire
//   raw_lineaire <entrée.RAF> <sortie.tif> [échelle=0.125]
import CoreImage
import Foundation

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage : raw_lineaire <raw> <sortie.tif> [échelle]\n".data(using: .utf8)!)
    exit(2)
}
let entree = URL(fileURLWithPath: args[1])
let sortie = URL(fileURLWithPath: args[2])
let echelle = args.count > 3 ? Float(args[3]) ?? 0.125 : 0.125

guard let raw = CIRAWFilter(imageURL: entree) else {
    FileHandle.standardError.write("RAW illisible : \(args[1])\n".data(using: .utf8)!)
    exit(1)
}
raw.boostAmount = 0              // réponse linéaire, pas de courbe de base
raw.boostShadowAmount = 0
raw.isGamutMappingEnabled = false
raw.exposure = 0
raw.shadowBias = 0
raw.localToneMapAmount = 0
raw.contrastAmount = 0
raw.extendedDynamicRangeAmount = 0
raw.sharpnessAmount = 0
raw.luminanceNoiseReductionAmount = 0
raw.colorNoiseReductionAmount = 0
raw.orientation = .up             // pas de rotation : même sens que les pixels stockés du JPG
raw.scaleFactor = echelle

guard let image = raw.outputImage else {
    FileHandle.standardError.write("développement impossible\n".data(using: .utf8)!)
    exit(1)
}
let lineaire = CGColorSpace(name: CGColorSpace.linearSRGB)!
let contexte = CIContext(options: [.workingColorSpace: lineaire])
do {
    try contexte.writeTIFFRepresentation(of: image, to: sortie, format: .RGBA16, colorSpace: lineaire, options: [:])
} catch {
    FileHandle.standardError.write("écriture impossible : \(error)\n".data(using: .utf8)!)
    exit(1)
}
print("\(Int(image.extent.width))x\(Int(image.extent.height)) \(sortie.path)")
