# Loudness Processing for Podcasts

Dieses Dokument erklärt die neuen Loudness-Processing-Features von ClearVoice.

## Übersicht

ClearVoice bietet jetzt professionelle Lautstärke-Normalisierung und Dynamik-Kompression für Podcast-Audio. Dies sorgt dafür, dass Sprachaufnahmen konsistent klingen und nicht ständig die Lautstärke angepasst werden muss.

### Verarbeitungskette (Processing Chain)

Wenn "Lautstärke-Optimierung" aktiviert ist, werden die folgenden Schritte in dieser Reihenfolge ausgeführt:

```
Eingabe-Audio
    ↓
[1] Speech Enhancement (MossFormer2_SE_48K)
    → Entfernt Hintergrundgeräusche
    ↓
[2] Loudness Normalization (LUFS-basiert)
    → Normalisiert zu -16 LUFS (Apple Podcasts Standard)
    ↓
[3] Dynamic Range Compression
    → Ratio 4:1, macht leise Stellen lauter, laute Stellen leiser
    ↓
[4] Peak Limiting
    → Verhindert Clipping bei -1 dB
    ↓
Sauberes, konsistent klingendes Ausgabe-Audio
```

## Verwendung in der GUI

### Option 1: Nur Speech Enhancement (Standard)
```
[Checkbox] Super-Resolution (48kHz)
[Checkbox] Lautstärke-Optimierung          ← NICHT AKTIVIERT
[Checkbox] Video mit Audio remuxen
```

**Ergebnis:** Nur Entrauschung, keine Lautstärke-Anpassung.

### Option 2: Speech Enhancement + Loudness Optimization (Empfohlen für Podcasts)
```
[Checkbox] Super-Resolution (48kHz)
[✓] Lautstärke-Optimierung                 ← AKTIVIERT
[Checkbox] Video mit Audio remuxen
```

**Ergebnis:** Entrauschung + professionelle Lautstärke-Normalisierung und Kompression.

## Verwendung im Code

```python
from clearvoice import ClearVoice

# Ohne Loudness Processing
myClearVoice = ClearVoice(
    task='speech_enhancement',
    model_names=['MossFormer2_SE_48K'],
    apply_loudness_processing_flag=False  # Standard
)

# Mit Loudness Processing
myClearVoice = ClearVoice(
    task='speech_enhancement',
    model_names=['MossFormer2_SE_48K'],
    apply_loudness_processing_flag=True   # Aktiviert!
)

# Audio verarbeiten
output = myClearVoice(input_path='podcast.wav', online_write=False)
myClearVoice.write(output, output_path='podcast_processed.wav')
```

Siehe auch: `clearvoice/demo_loudness_processing.py` für vollständige Beispiele.

## Technische Details

### Was ist LUFS?

**LUFS** = Loudness Units relative to Full Scale

LUFS ist der professionelle Standard zur Messung der wahrgenommenen Lautstärke:

- **-16 LUFS:** Apple Podcasts Standard (empfohlen)
- **-14 LUFS:** Spotify Standard (etwas lauter)
- **-13 LUFS:** YouTube Standard
- **-20 LUFS:** Ruhigerer, natürlicherer Sound

Im Gegensatz zu Peak-Normalisierung (die nur auf den höchsten Lautstärke-Spike schaut), misst LUFS wie der menschliche Gehörsinn die durchschnittliche Lautstärke wirklich wahrnimmt.

### Dynamic Range Compression

Der Kompressor reduziert die Dynamik zwischen leisen und lauten Teilen:

| Parameter | Standardwert | Effekt |
|-----------|--------------|--------|
| **Ratio** | 4:1 | Komprimiert um Faktor 4 (subtil, natürlich) |
| **Threshold** | -20 dB | Kompression startet bei -20 dB |
| **Attack** | 20 ms | Kompression aktiviert in 20 Millisekunden |
| **Release** | 100 ms | Kompression lässt los in 100 Millisekunden |
| **Knee** | 2 dB | Sanfte Übergänge statt abrupter Start |

**Beispiel:** Mit Ratio 4:1 und Threshold -20 dB:
- Wenn Audio auf -10 dB geht (10 dB über Schwelle)
- Wird es komprimiert auf: -20 + (10 / 4) = -17.5 dB
- Also 10 dB Spitze wird zu 2.5 dB → viel kontrolierter!

### Peak Limiting

Ein Limiter ist ein Kompressor mit unendliches Ratio (1:∞):
- **Threshold:** -1 dB
- **Funktion:** Hard brick-wall limiting - verhindert, dass Peaks -1 dB übersteigen
- **Sicherheit:** Verhindert digitales Clipping

## Ausgabe-Statistiken

Nach jeder Verarbeitung werden Statistiken angezeigt:

```
=== Loudness Processing Results ===
Normalization:
  Before: -28.5 LUFS
  After:  -16.0 LUFS
  Gain:   +12.5 dB
Compression:
  Ratio:  4.0:1
  Threshold: -20.0 dB
  Avg Reduction: -0.45 dB
  Max Reduction: -2.15 dB
Limiting:
  Peak Before: -2.3 dB
  Peak After:  -1.0 dB
  Samples Limited: 1240

Overall:
  Input Peak:  -2.3 dB
  Output Peak: -1.0 dB
```

Das zeigt dir genau, was mit deinem Audio passiert ist.

## Einstellungen anpassen

Alle Loudness-Processing-Parameter sind dokumentiert in:

```
clearvoice/utils/loudness_settings.py
```

**Wichtig:** Dieses Datei hat ausführliche Kommentare erklärt:
- Was jeder Parameter macht
- Welche Wertebereiche sinnvoll sind
- Wie Änderungen den Sound beeinflussen

Falls du jemals Parameter anpassen möchtest (z.B. für sehr dynamische Sprecher), öffne diese Datei und lies die Kommentare!

### Schnellreferenz: Häufige Szenarios

```python
# SZENARIO 1: Normaler, konsistenter Sprecher (Standard)
# → Nutze die Default-Werte (keine Änderungen nötig)

# SZENARIO 2: Sehr dynamischer Sprecher (viel Lautstärke-Variation)
DynamicRangeCompressor.RATIO = 5.0
DynamicRangeCompressor.THRESHOLD = -25.0
# → Aggressivere Kompression für bessere Kontrolle

# SZENARIO 3: Natürlicher, minimal bearbeiteter Sound
DynamicRangeCompressor.RATIO = 3.0
DynamicRangeCompressor.THRESHOLD = -15.0
# → Leichtere Kompression, mehr Dynamik erhalten

# SZENARIO 4: Sehr lauter, Radio-ähnlicher Sound
LoudnessNormalization.TARGET_LUFS = -14.0
DynamicRangeCompressor.RATIO = 4.5
ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = +2.0
# → Lauter gesamt, mehr Kompression, aggresivere Präsenz
```

## Häufig gestellte Fragen

### F: Sollte ich Lautstärke-Optimierung immer verwenden?

**A:** Für Podcasts: Ja! Es sorgt für professionellen, konsistenten Sound.
Für andere Zwecke (z.B. Musik): Wahrscheinlich nein, da es zu viel Dynamik entfernt.

### F: Macht Lautstärke-Optimierung das Audio unnatürlich?

**A:** Nein, wenn die Parameter richtig eingestellt sind. Die 4:1 Kompression ist sanft genug, um natürlich zu klingen. Du bekommst keinen "Radio-Station-Pumping-Effekt" wie bei aggressiver Kompression.

### F: Kann ich die Parameter später noch anpassen?

**A:** Ja! Die Parameter sind in `loudness_settings.py` dokumentiert. Jeder Parameter hat ausführliche Kommentare, die erklären, wie man ihn anpasst und was die Effekte sind.

### F: Was ist der Unterschied zwischen LUFS und dB?

**A:**
- **dB:** Technische Messung basierend auf Amplitude (wie laut ein Signal technisch ist)
- **LUFS:** Psychoakustische Messung (wie laut es sich für Menschen anfühlt)

LUFS ist besser für Sprache/Podcasts, weil es berücksichtigt, wie das menschliche Ohr Lautstärke wirklich wahrnimmt.

### F: Mein Audio klingt zu laut oder zu leise nach Verarbeitung?

**A:** Das ist normalerweise kein Problem mit dem Processing selbst. Aber wenn du es anpassen möchtest:

1. Schaue dir die Ausgabe-Statistiken an
2. Passe `FINAL_GAIN_ADJUSTMENT_DB` in `loudness_settings.py` an
   - Positiver Wert = lauter
   - Negativer Wert = leiser

### F: Sollte ich auch Super-Resolution verwenden?

**A:** Das ist unabhängig:
- **Lautstärke-Optimierung:** Für konsistente Lautstärke
- **Super-Resolution:** Für bessere Audio-Qualität (8kHz → 48kHz)

Du kannst beide zusammen verwenden! Aktiviere einfach beide Checkboxen.

## Best Practices

1. **Immer Speech Enhancement zuerst:** Das bereitet das Audio vor
2. **Dann Loudness Processing:** Normalisiert das saubere Signal
3. **Höre das Ergebnis an:** Jede Stimme ist anders
4. **Parametern anpassen nur wenn nötig:** Die Defaults funktionieren für 90% der Podcasts

## Weitere Ressourcen

- [Descript: Podcast Loudness Standards 2025](https://www.descript.com/blog/article/podcast-loudness-standard-getting-the-right-volume)
- [Auphonic: Loudness Normalization for Podcasts](https://auphonic.com/blog/2011/07/25/loudness-normalization-and-compression-podcasts-and-speech-audio/)
- [Apple Podcasts Loudness Specification](https://podcasters.apple.com/resources/sound-design/podcast-loudness)
- Code-Demo: `clearvoice/demo_loudness_processing.py`
- Detaillierte Parameter: `clearvoice/utils/loudness_settings.py`

## Zusammenfassung

Mit "Lautstärke-Optimierung" erhältst du:

✅ Professionelle Podcast-Sound-Qualität
✅ Konsistente Lautstärke über mehrere Takes
✅ Keine Clipping-Probleme
✅ Apple-Podcasts-kompatible LUFS-Normalisierung
✅ Natürlich klingende Kompression (nicht übertrieben)
✅ Vollständig dokumentierte, anpassbare Parameter

Das ist genau das, was Podcast-Produzenten brauchen!
