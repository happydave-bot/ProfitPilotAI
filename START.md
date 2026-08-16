# ProfitPilotAI starten

## 1. Projekt aktualisieren

```powershell
git pull
```

## 2. Tests ausführen

```powershell
py -m pytest tests -v
```

## 3. Live-Konfiguration prüfen — ohne Netzwerkzugriff

```powershell
py run_live.py --check
```

Der Check prüft Amazon-, eBay- und Suchbegriff-Konfiguration sowie die wichtigsten Kostenparameter. Es werden dabei keine API- oder Telegram-Anfragen gesendet.

## 4. Erster echter Testlauf — sicher

Einen einzelnen Suchbegriff in `PROFITPILOT_QUERY` setzen und anschließend:

```powershell
py run_live.py --once --dry-run
```

`--once` beendet den Prozess nach einem Scan. `--dry-run` verhindert den Telegram-Versand.

## 5. Normalen Live-Betrieb erst danach starten

```powershell
py run_live.py
```

Für echte Amazon-/eBay-Daten müssen die entsprechenden API-Zugangsdaten konfiguriert sein. Telegram wird erst für den normalen Betrieb benötigt.
