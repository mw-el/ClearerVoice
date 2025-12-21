# Quick Start: Lautstärke-Optimierung für Podcasts

## 🚀 Schnellstart in der GUI

### Schritt 1: Audio-Datei auswählen
- Links im "Dateien durchsuchen" Panel deine Podcast-MP3 oder WAV auswählen
- Doppelklick oder Button "Ausgewählte hinzufügen"

### Schritt 2: Lautstärke-Optimierung aktivieren
Rechts oben findest du folgende Checkboxen:

```
☑ Super-Resolution (48kHz)           ← Optional: für bessere Qualität
☑ Lautstärke-Optimierung             ← AKTIVIERE DIESE!
☑ Video mit Audio remuxen           ← Nur für Videos
```

**NUR "Lautstärke-Optimierung" ankreuzen** für standard Podcast-Processing.

### Schritt 3: Verarbeiten
- Button "Dateien verarbeiten" drücken
- Warten (dauert je nach Dateigröße 1-10 Minuten)
- Fertig! Die verarbeitete Datei liegt im selben Verzeichnis

### Ergebnis
- Original: `podcast.wav`
- Verarbeitet: `podcast-cleaned-20250221143022.wav`
  - Entrauscht
  - Lautstärke normalisiert zu -16 LUFS
  - Komprimiert für gleichmäßige Lautstärke
  - Professional-ready

---

## 📊 Was passiert beim Processing?

```
Dein Original-Audio (vielleicht zu leise, zu laut, mit Rauschen)
    ↓
[1] ENTRAUSCHUNG (Speech Enhancement)
    → Hintergrundgeräusche weg
    ↓
[2] LAUTSTÄRKE-NORMALISIERUNG (-16 LUFS)
    → Konsistente Lautstärke-Level
    ↓
[3] KOMPRESSION (4:1 Ratio)
    → Leise Stellen lauter, laute leiser
    ↓
[4] LIMITING (Sicherheit)
    → Kein Clipping, Peaks bei -1 dB
    ↓
FERTIG: Professioneller Podcast-Sound
```

---

## ✅ Wie klingt das Ergebnis?

**Vorher (typischer selbstaufgenommener Podcast):**
- Einige Stellen sehr leise, muss ich Ohr zum Lautsprecher halten
- Einige Stellen sehr laut, muss ich Volume runterdrehen
- Hintergrund-Rauschen manchmal hörbbar
- Ungleichmäßig, nicht professionell

**Nachher (mit Lautstärke-Optimierung):**
- Durchgehend gute Lautstärke - keine Anpassung nötig
- Laute und leise Stellen gleichmäßig ausgedrückt
- Sauberer, kein Rauschen
- Professionell wie bei großen Podcasts (Apple, Spotify, etc.)

---

## 🎚️ Feineinstellungen (Optional)

Falls das Ergebnis noch nicht perfekt ist, kannst du Parameter anpassen:

**Datei:** `clearvoice/utils/loudness_settings.py`

### Die 3 wichtigsten Parameter:

#### 1. Zu leise oder zu laut gesamt?
```python
ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = 0.0  # Standard

# Falls zu leise:
ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = +2.0  # +2 dB lauter

# Falls zu laut:
ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = -2.0  # -2 dB leiser
```

#### 2. Zu viel Kompression (klingt "gepresst")?
```python
DynamicRangeCompressor.RATIO = 4.0  # Standard (sanft)

# Für mehr Natürlichkeit:
DynamicRangeCompressor.RATIO = 3.0  # Weniger Kompression

# Für mehr Kontrolle:
DynamicRangeCompressor.RATIO = 5.0  # Mehr Kompression
```

#### 3. Sehr dynamischer Sprecher (viel Lautstärke-Variation)?
```python
DynamicRangeCompressor.THRESHOLD = -20.0  # Standard

# Für mehr Kontrolle:
DynamicRangeCompressor.THRESHOLD = -25.0  # Aggressivere Kompression
```

**Wichtig:** Jede Änderung erfordert Neustart der App!

---

## 🔧 Einstellungen für verschiedene Szenarien

### Szenario A: Normal sprechen, mit Hintergrundgeräuschen
**Empfehlung:** Standard-Einstellungen verwenden (nichts ändern)

```python
# clearvoice/utils/loudness_settings.py
LoudnessNormalization.TARGET_LUFS = -16.0
DynamicRangeCompressor.RATIO = 4.0
DynamicRangeCompressor.THRESHOLD = -20.0
```

### Szenario B: Sprecher mit großen Lautstärke-Unterschieden
**Empfehlung:** Aggressivere Kompression

```python
# clearvoice/utils/loudness_settings.py
DynamicRangeCompressor.RATIO = 5.0
DynamicRangeCompressor.THRESHOLD = -25.0
```

### Szenario C: Sehr leise Sprachaufnahmen
**Empfehlung:** Höheres Ziel + Final Gain Boost

```python
# clearvoice/utils/loudness_settings.py
LoudnessNormalization.TARGET_LUFS = -14.0  # Etwas lauter
ProcessingConfig.FINAL_GAIN_ADJUSTMENT_DB = +3.0  # Extra Boost
```

### Szenario D: Natürlicher Sound, minimal bearbeitet
**Empfehlung:** Sanftere Kompression

```python
# clearvoice/utils/loudness_settings.py
DynamicRangeCompressor.RATIO = 3.0
DynamicRangeCompressor.THRESHOLD = -15.0
```

---

## 📈 Ausgabe-Statistiken verstehen

Nach der Verarbeitung siehst du im Status-Fenster:

```
=== Loudness Processing Results ===
Normalization:
  Before: -28.5 LUFS        ← Dein Original war sehr leise
  After:  -16.0 LUFS        ← Jetzt Apple-Podcasts Standard
  Gain:   +12.5 dB          ← So viel lauter wurde es

Compression:
  Ratio:  4.0:1             ← 4x Kompression
  Threshold: -20.0 dB       ← Ab hier komprimiert
  Avg Reduction: -0.45 dB   ← Im Schnitt 0.45 dB reduziert
  Max Reduction: -2.15 dB   ← Maximal 2.15 dB bei Peaks

Limiting:
  Peak Before: -2.3 dB      ← Höchster Peak vorher
  Peak After:  -1.0 dB      ← Höchster Peak nachher (limitiert)
  Samples Limited: 1240     ← Wie oft der Limiter aktiviert war

Overall:
  Input Peak:  -2.3 dB
  Output Peak: -1.0 dB
```

**Was bedeutet das?**
- Dein Audio wurde um 12.5 dB lauter gemacht (weil es zu leise war)
- Der Kompressor hat gemailt, durchschnittlich 0.45 dB zu reduzieren
- Der Limiter hat 1240 Spitzen erwischt und auf -1 dB begrenzt
- Keine Clipping-Probleme (Peak nie über -1 dB)

---

## ❓ Häufige Fragen

### F: Soll ich "Super-Resolution" auch aktivieren?
**A:** Das ist optional und unabhängig:
- Super-Resolution: verbessert die Audio-Qualität (8kHz → 48kHz)
- Lautstärke-Optimierung: normalisiert die Lautstärke

Du kannst beide zusammen verwenden, oder nur die Lautstärke-Optimierung.

### F: Wie lange dauert die Verarbeitung?
**A:** Abhängig von Dateigröße:
- 1 Stunde Podcast: ~3-5 Minuten
- Schnelligkeit hängt von deiner GPU ab

Die App zeigt "Verarbeite..." während es läuft.

### F: Kann ich die verarbeitete Datei direkt hochladen?
**A:** Ja! Nach Verarbeitung ist die Datei sofort podcast-ready:
- Richtige Lautstärke für alle Plattformen
- Keine Clipping-Probleme
- Sauberer Sound ohne Rauschen

### F: Was ist der Unterschied zwischen den Buttons?

**Option 1: Keine Checkbox aktiviert**
→ Nur Entrauschung (Speech Enhancement)

**Option 2: Nur "Lautstärke-Optimierung" aktiviert**
→ Entrauschung + Lautstärke-Normalisierung (EMPFOHLEN)

**Option 3: Beide aktiviert**
→ Entrauschung + Super-Resolution + Lautstärke-Optimierung

### F: Mein Audio klingt nach der Verarbeitung komisch?
**A:** Das ist normalerweise nicht das Processing selbst. Aber:

1. **Zu leise/laut?** → Passe `FINAL_GAIN_ADJUSTMENT_DB` an
2. **Zu sehr "gepresst"?** → Reduziere `RATIO` (z.B. 3.0 statt 4.0)
3. **Zu subtil?** → Erhöhe `RATIO` (z.B. 5.0 statt 4.0)

Alle Parameter sind dokumentiert in `clearvoice/utils/loudness_settings.py`

### F: Kann ich mehrere Dateien auf einmal verarbeiten?
**A:** Ja! Einfach mehrere Dateien in die Liste auf der rechten Seite hinzufügen.

App verarbeitet sie nacheinander:
```
[1/5] podcast_episode_1.mp3
  → verarbeitet
[2/5] podcast_episode_2.mp3
  → verarbeitet
...
```

---

## 📚 Weiterführende Dokumente

- **Detaillierte Dokumentation:** `LOUDNESS_PROCESSING.md`
- **Code-Beispiele:** `clearvoice/demo_loudness_processing.py`
- **Alle Parameter dokumentiert:** `clearvoice/utils/loudness_settings.py`
- **Audio-Processing-Code:** `clearvoice/utils/audio_processing.py`

---

## 🎯 Zusammenfassung

1. **Aktiviere "Lautstärke-Optimierung" in der GUI** ✅
2. **Wähle deine Podcast-Datei** ✅
3. **Drücke "Dateien verarbeiten"** ✅
4. **Fertig!** Die Datei ist podcast-ready ✅

Die Standardeinstellungen funktionieren für 90% aller Podcast-Use-Cases.

Viel Erfolg mit deinem Podcast!

---

*Fragen? Lies die vollständige Dokumentation: `LOUDNESS_PROCESSING.md`*
