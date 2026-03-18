# AbschleppApp - Datenbankstruktur & Rollenkonzept

## Übersicht

Die Anwendung verwendet **MongoDB** als Datenbank mit folgenden Collections:

| Collection | Beschreibung | Anzahl Dokumente |
|------------|--------------|------------------|
| `users` | Alle Benutzer (Admin, Behörden, Abschleppdienste) | 7 |
| `jobs` | Abschleppaufträge | 17 |
| `audit_logs` | Protokollierung aller Aktionen | 456 |

---

## 1. Collection: `users`

### 1.1 Rollen (UserRole)

| Rolle | Wert | Beschreibung |
|-------|------|--------------|
| **Admin** | `admin` | System-Administrator |
| **Behörde** | `authority` | Ordnungsamt, Polizei etc. (Haupt-Account oder Mitarbeiter) |
| **Abschleppdienst** | `towing_service` | Abschleppunternehmen |

### 1.2 Genehmigungsstatus (ApprovalStatus)

| Status | Wert | Beschreibung |
|--------|------|--------------|
| Ausstehend | `pending` | Wartet auf Admin-Freischaltung |
| Genehmigt | `approved` | Freigeschaltet, kann sich einloggen |
| Abgelehnt | `rejected` | Registrierung abgelehnt |

---

### 1.3 Benutzer-Felder (alle Rollen)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `_id` | ObjectId | ✅ | MongoDB interne ID |
| `id` | String (UUID) | ✅ | Anwendungs-ID |
| `email` | String | ✅ | E-Mail-Adresse (unique) |
| `password` | String | ✅ | Gehashtes Passwort (bcrypt) |
| `role` | String | ✅ | `admin`, `authority`, `towing_service` |
| `name` | String | ✅ | Anzeigename |
| `created_at` | String (ISO) | ✅ | Erstellungsdatum |
| `approval_status` | String | ❌ | `pending`, `approved`, `rejected` |
| `blocked` | Boolean | ❌ | Gesperrt durch Admin |
| `totp_enabled` | Boolean | ❌ | 2FA aktiviert |
| `totp_secret` | String | ❌ | TOTP-Geheimnis (nur wenn 2FA Setup läuft) |
| `email_verified` | Boolean | ❌ | E-Mail verifiziert |

---

### 1.4 Zusätzliche Felder: ADMIN

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| - | - | Keine zusätzlichen Felder |

**Berechtigungen Admin:**
- ✅ Alle Benutzer sehen und verwalten
- ✅ Registrierungen genehmigen/ablehnen
- ✅ Benutzer sperren/entsperren
- ✅ Passwörter zurücksetzen
- ✅ Alle Aufträge sehen
- ✅ DSGVO-Cleanup manuell triggern
- ✅ Audit-Logs einsehen

---

### 1.5 Zusätzliche Felder: AUTHORITY (Behörde)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `authority_name` | String | ✅ | Name der Behörde (z.B. "Ordnungsamt Berlin-Mitte") |
| `department` | String | ❌ | Abteilung |
| `dienstnummer` | String | ✅ | Automatisch generiert (z.B. "DN-CECA-001") |
| `is_main_authority` | Boolean | ✅ | `true` = Haupt-Account, `false` = Mitarbeiter |
| `parent_authority_id` | String | ❌ | ID des Haupt-Accounts (nur bei Mitarbeitern) |
| `linked_services` | Array[String] | ❌ | IDs der verknüpften Abschleppdienste |

#### Behörde: Haupt-Account (`is_main_authority: true`)

**Berechtigungen:**
- ✅ Aufträge erstellen
- ✅ Abschleppdienste per Code verknüpfen
- ✅ Abschleppdienste entfernen
- ✅ Mitarbeiter-Accounts erstellen
- ✅ Mitarbeiter sperren/entsperren
- ✅ Eigene Aufträge sehen (alle der Behörde)
- ✅ 2FA aktivieren/deaktivieren

#### Behörde: Mitarbeiter-Account (`is_main_authority: false`)

**Berechtigungen:**
- ✅ Aufträge erstellen
- ✅ Verknüpfte Abschleppdienste sehen (READ-ONLY, vom Haupt-Account)
- ✅ Eigene Aufträge sehen
- ✅ 2FA aktivieren/deaktivieren
- ❌ **KEINE** Abschleppdienste verknüpfen/entfernen
- ❌ **KEINE** Mitarbeiter erstellen

---

### 1.6 Zusätzliche Felder: TOWING_SERVICE (Abschleppdienst)

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `company_name` | String | ✅ | Firmenname |
| `phone` | String | ✅ | Telefonnummer |
| `address` | String | ✅ | Firmenadresse |
| `yard_address` | String | ✅ | Hofadresse (wo Fahrzeuge stehen) |
| `yard_lat` | Float | ❌ | Hof-Koordinate Latitude |
| `yard_lng` | Float | ❌ | Hof-Koordinate Longitude |
| `opening_hours` | String | ❌ | Öffnungszeiten |
| `service_code` | String | ✅ | 6-stelliger Verknüpfungscode (auto-generiert) |
| `linked_authorities` | Array[String] | ❌ | IDs der Behörden, die verknüpft sind |
| `business_license` | String (Base64) | ❌ | Gewerbeanmeldung |
| **Preise:** | | |
| `tow_cost` | Float | ❌ | Abschleppkosten (Standard) |
| `daily_cost` | Float | ❌ | Standgebühren pro Tag |
| `processing_fee` | Float | ❌ | Bearbeitungsgebühr |
| `empty_trip_fee` | Float | ❌ | Leerfahrt-Pauschale |
| `night_surcharge` | Float | ❌ | Nachtzuschlag |
| `weekend_surcharge` | Float | ❌ | Wochenendzuschlag |
| `heavy_vehicle_surcharge` | Float | ❌ | Schwerlastzuschlag (>3,5t) |
| **Zeitbasierte Abrechnung:** | | |
| `time_based_enabled` | Boolean | ❌ | Zeitbasierte Abrechnung aktiv |
| `first_half_hour` | Float | ❌ | Kosten erste halbe Stunde |
| `additional_half_hour` | Float | ❌ | Kosten jede weitere halbe Stunde |

**Berechtigungen Abschleppdienst:**
- ✅ Aufträge annehmen/ablehnen
- ✅ Status aktualisieren (vor Ort → abgeschleppt → im Hof)
- ✅ Fahrzeug freigeben
- ✅ Fotos hinzufügen
- ✅ Notizen hinzufügen
- ✅ Kosten berechnen
- ✅ Service-Code teilen (zur Verknüpfung)
- ✅ Preise konfigurieren
- ✅ 2FA aktivieren/deaktivieren

---

## 2. Collection: `jobs`

### 2.1 Auftragsstatus (JobStatus)

| Status | Wert | Beschreibung |
|--------|------|--------------|
| Ausstehend | `pending` | Neu erstellt, wartet auf Zuweisung |
| Zugewiesen | `assigned` | Einem Abschleppdienst zugewiesen |
| Vor Ort | `on_site` | Abschleppdienst ist vor Ort |
| Abgeschleppt | `towed` | Fahrzeug wird transportiert |
| Im Hof | `in_yard` | Fahrzeug steht auf dem Hof |
| Freigegeben | `released` | Fahrzeug wurde abgeholt |

### 2.2 Auftrags-Felder

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `_id` | ObjectId | ✅ | MongoDB interne ID |
| `id` | String (UUID) | ✅ | Anwendungs-ID |
| `job_number` | String | ✅ | Auftragsnummer (z.B. "TOW-20260224-YS1DHO") |
| **Fahrzeugdaten:** | | |
| `license_plate` | String | ❌ | Kennzeichen (z.B. "B-AB 1234") |
| `vin` | String | ❌ | Fahrzeug-Identifizierungsnummer (17 Zeichen) |
| **Standort:** | | |
| `location_address` | String | ✅ | Abschleppstandort (Adresse) |
| `location_lat` | Float | ✅ | Latitude |
| `location_lng` | Float | ✅ | Longitude |
| **Auftragsdetails:** | | |
| `tow_reason` | String | ✅ | Abschleppgrund |
| `job_type` | String | ❌ | `towing` oder `sicherstellung` |
| `notes` | String | ❌ | Behörden-Notizen |
| `photos` | Array[String] | ❌ | Behörden-Fotos (Base64 oder URL) |
| `status` | String | ✅ | Aktueller Status |
| **Ersteller:** | | |
| `created_by_id` | String | ✅ | ID des Erstellers |
| `created_by_name` | String | ✅ | Name des Erstellers |
| `created_by_authority` | String | ❌ | Behördenname |
| `created_by_dienstnummer` | String | ❌ | Dienstnummer des Erstellers |
| `authority_id` | String | ✅ | ID der zugehörigen Behörde |
| `created_by_service` | Boolean | ❌ | `true` wenn vom Abschleppdienst erstellt |
| **Abschleppdienst:** | | |
| `assigned_service_id` | String | ❌ | ID des zugewiesenen Dienstes |
| `assigned_service_name` | String | ❌ | Name des zugewiesenen Dienstes |
| `service_notes` | String | ❌ | Notizen vom Abschleppdienst |
| `service_photos` | Array[String] | ❌ | Fotos vom Abschleppdienst |
| **Halter/Abholung:** | | |
| `owner_first_name` | String | ❌ | Vorname des Abholers |
| `owner_last_name` | String | ❌ | Nachname des Abholers |
| `owner_address` | String | ❌ | Adresse des Abholers |
| **Zahlung:** | | |
| `payment_method` | String | ❌ | `cash`, `card`, `invoice` |
| `payment_amount` | Float | ❌ | Bezahlter Betrag |
| `calculated_costs` | Object | ❌ | Berechnete Kosten (Aufschlüsselung) |
| **Zeitstempel:** | | |
| `created_at` | String (ISO) | ✅ | Erstellungszeitpunkt |
| `updated_at` | String (ISO) | ✅ | Letzte Aktualisierung |
| `accepted_at` | String (ISO) | ❌ | Annahme durch Abschleppdienst |
| `on_site_at` | String (ISO) | ❌ | Ankunft vor Ort |
| `towed_at` | String (ISO) | ❌ | Fahrzeug abgeschleppt |
| `in_yard_at` | String (ISO) | ❌ | Ankunft im Hof |
| `released_at` | String (ISO) | ❌ | Freigabe/Abholung |
| **Sicherstellung (optional):** | | |
| `sicherstellung_reason` | String | ❌ | Grund der Sicherstellung |
| `vehicle_category` | String | ❌ | `under_3_5t` oder `over_3_5t` |
| `ordering_authority` | String | ❌ | Anordnende Behörde |
| `contact_attempts` | Boolean | ❌ | Halter kontaktiert? |
| `contact_attempts_notes` | String | ❌ | Notizen zur Kontaktaufnahme |
| `estimated_vehicle_value` | Float | ❌ | Geschätzter Fahrzeugwert |
| **Leerfahrt:** | | |
| `is_empty_trip` | Boolean | ❌ | Leerfahrt (Fahrzeug nicht vorgefunden) |
| **DSGVO:** | | |
| `anonymized` | Boolean | ❌ | Legacy-Flag |
| `personal_data_anonymized` | Boolean | ❌ | Personendaten anonymisiert |
| `personal_data_anonymized_at` | String (ISO) | ❌ | Anonymisierungszeitpunkt |
| `invoice_data_deleted` | Boolean | ❌ | Rechnungsdaten gelöscht (nach 10 Jahren) |

---

## 3. Collection: `audit_logs`

### 3.1 Audit-Log Felder

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `_id` | ObjectId | MongoDB interne ID |
| `id` | String (UUID) | Anwendungs-ID |
| `timestamp` | String (ISO) | Zeitstempel der Aktion |
| `action` | String | Aktionstyp (siehe unten) |
| `user_id` | String | ID des ausführenden Benutzers |
| `user_name` | String | Name/E-Mail des Benutzers |
| `details` | Object | Zusätzliche Details zur Aktion |
| `created_at` | String (ISO) | Erstellungszeitpunkt |

### 3.2 Aktionstypen

| Aktion | Beschreibung |
|--------|--------------|
| `LOGIN` | Erfolgreicher Login |
| `LOGIN_FAILED` | Fehlgeschlagener Login |
| `LOGIN_2FA` | Login mit 2FA |
| `LOGOUT` | Logout |
| `REGISTER` | Neue Registrierung |
| `USER_APPROVED` | Benutzer genehmigt |
| `USER_REJECTED` | Benutzer abgelehnt |
| `USER_BLOCKED` | Benutzer gesperrt |
| `USER_UNBLOCKED` | Benutzer entsperrt |
| `PASSWORD_RESET` | Passwort zurückgesetzt |
| `2FA_ENABLED` | 2FA aktiviert |
| `2FA_DISABLED` | 2FA deaktiviert |
| `JOB_CREATED` | Auftrag erstellt |
| `JOB_UPDATED` | Auftrag aktualisiert |
| `JOB_STATUS_CHANGED` | Status geändert |
| `SERVICE_LINKED` | Abschleppdienst verknüpft |
| `SERVICE_UNLINKED` | Abschleppdienst entfernt |
| `EMPLOYEE_CREATED` | Mitarbeiter erstellt |
| `DSGVO_PERSONAL_DATA_CLEANUP` | DSGVO-Cleanup durchgeführt |
| `STEUERRECHT_DATA_CLEANUP` | Steuerrecht-Cleanup (10 Jahre) |

---

## 4. Beziehungen zwischen Entitäten

```
┌─────────────────────────────────────────────────────────────────┐
│                          ADMIN                                   │
│  - Verwaltet alle Benutzer                                      │
│  - Genehmigt Registrierungen                                    │
│  - Sieht alle Aufträge                                          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                │ genehmigt
                                ▼
┌────────────────────────┐              ┌────────────────────────┐
│   BEHÖRDE (Haupt)      │◄────────────►│   ABSCHLEPPDIENST      │
│  is_main_authority:    │  verknüpft   │                        │
│        true            │  via Code    │  service_code: "ABC123"│
│                        │              │                        │
│  linked_services: [    │              │  linked_authorities: [ │
│    service_id_1,       │              │    authority_id_1      │
│    service_id_2        │              │  ]                     │
│  ]                     │              │                        │
└────────────────────────┘              └────────────────────────┘
         │                                         │
         │ erstellt                                │
         ▼                                         │
┌────────────────────────┐                         │
│   BEHÖRDE (Mitarbeiter)│                         │
│  is_main_authority:    │                         │
│        false           │                         │
│                        │                         │
│  parent_authority_id:  │                         │
│    [Haupt-Account-ID]  │                         │
│                        │                         │
│  linked_services:      │◄────────────────────────┘
│    [erbt vom Parent]   │     sieht (read-only)
└────────────────────────┘

                    │
                    │ erstellt
                    ▼
         ┌─────────────────────┐
         │        JOB          │
         │                     │
         │  authority_id       │
         │  assigned_service_id│
         │  status             │
         └─────────────────────┘
```

---

## 5. DSGVO & Steuerrecht

### 5.1 Aufbewahrungsfristen

| Datentyp | Frist | Aktion |
|----------|-------|--------|
| Personenbezogene Daten | 6 Monate (180 Tage) | Anonymisierung |
| Rechnungsdaten | 10 Jahre | Löschung/Markierung |

### 5.2 Anonymisierte Felder (nach 6 Monaten)

- `license_plate` → "*** (DSGVO-Anonymisiert)"
- `vin` → "*** (DSGVO-Anonymisiert)"
- `owner_name` → "*** (DSGVO-Anonymisiert)"
- `owner_address` → "*** (DSGVO-Anonymisiert)"
- `owner_phone` → "*** (DSGVO-Anonymisiert)"
- `photos` → [] (gelöscht)

### 5.3 Erhaltene Rechnungsdaten (10 Jahre)

- `job_number`
- `tow_cost`, `daily_cost`, `total_cost`
- `payment_method`, `payment_amount`
- `authority_name`, `service_name`
- `tow_reason`
- `created_at`, `released_at`

---

## 6. Aktuelle Benutzer in der Datenbank

| E-Mail | Rolle | Haupt/Mitarbeiter | Verknüpfte Services |
|--------|-------|-------------------|---------------------|
| admin@test.de | Admin | - | - |
| admin@abschleppapp.de | Admin | - | - |
| behoerde@test.de | Behörde | **Haupt** | 2 Services |
| behoerde1@test.de | Behörde | Mitarbeiter | 1 Service (vom Parent) |
| maxitaxi@gmail.com | Behörde | Mitarbeiter | 2 Services (vom Parent) |
| abschlepp@test.de | Abschleppdienst | - | 1 Behörde |
| praxis@beispiel.com | Abschleppdienst | - | 1 Behörde |

---

## 7. API-Endpunkte nach Rolle

### Admin-Endpunkte
- `GET /api/admin/users` - Alle Benutzer
- `GET /api/admin/jobs` - Alle Aufträge
- `POST /api/admin/approve/{id}` - Benutzer genehmigen
- `POST /api/admin/users/{id}/block` - Benutzer sperren
- `GET /api/admin/audit-logs` - Audit-Logs
- `GET /api/admin/dsgvo-status` - DSGVO-Status
- `POST /api/admin/trigger-cleanup` - DSGVO-Cleanup

### Behörden-Endpunkte
- `GET /api/jobs` - Eigene Aufträge
- `POST /api/jobs` - Auftrag erstellen
- `GET /api/services` - Verknüpfte Abschleppdienste
- `POST /api/services/link` - Dienst verknüpfen (nur Haupt)
- `DELETE /api/services/unlink/{id}` - Dienst entfernen (nur Haupt)
- `GET /api/employees` - Mitarbeiter auflisten (nur Haupt)
- `POST /api/employees` - Mitarbeiter erstellen (nur Haupt)

### Abschleppdienst-Endpunkte
- `GET /api/jobs` - Zugewiesene Aufträge
- `PUT /api/jobs/{id}` - Auftrag aktualisieren
- `PUT /api/profile/costs` - Preise aktualisieren
- `GET /api/profile/service-code` - Verknüpfungscode abrufen

### Öffentliche Endpunkte
- `GET /api/search/vehicle` - Fahrzeugsuche (Kennzeichen/FIN)
- `POST /api/auth/login` - Anmeldung
- `POST /api/auth/register` - Registrierung
