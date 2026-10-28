package com.nikonhacker.emu;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;

/** Capture du tampon d'écran d'interface (YCbCr 4:2:0, 640×480, pointeur en 0x83CE0230). */
public class Ecran {
    public static final int ADRESSE_BASE = 0x83CE0230;

    public static int base(D40Emu e) { return e.rd32(ADRESSE_BASE); }

    /** @return nombre de pixels de luminance non nuls (indicateur « quelque chose a été dessiné »). */
    public static int nonZero(D40Emu e, int y) {
        int n = 0;
        for (int i = 0; i < 640 * 480; i += 7) if (e.memory.loadUnsigned8(y + i, null) != 0) n++;
        return n;
    }

    public static BufferedImage image(D40Emu e, int y) {
        int cb = y + 0x4B000, cr = y + 0x5DC00;
        BufferedImage img = new BufferedImage(640, 480, BufferedImage.TYPE_INT_RGB);
        for (int j = 0; j < 480; j++) for (int i = 0; i < 640; i++) {
            int Y = e.memory.loadUnsigned8(y + j * 640 + i, null);
            int ci = (j >> 1) * 320 + (i >> 1);
            int U = e.memory.loadUnsigned8(cb + ci, null) - 128, V = e.memory.loadUnsigned8(cr + ci, null) - 128;
            double yy = 1.164 * (Y - 16);
            int r = clamp(yy + 1.596 * V), g = clamp(yy - 0.392 * U - 0.813 * V), b = clamp(yy + 2.017 * U);
            img.setRGB(i, j, (r << 16) | (g << 8) | b);
        }
        return img;
    }

    static int clamp(double v) { return v < 0 ? 0 : v > 255 ? 255 : (int) v; }

    public static void png(D40Emu e, int y, File f) throws IOException {
        javax.imageio.ImageIO.write(image(e, y), "png", f);
    }
}
