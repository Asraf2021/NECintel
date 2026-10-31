# Texniki izah sənədi

**Layihə:** Smart Transit & Crowdsourcing Engine
**Müsabiqə:** Digital Azerbaijan Challenge 2026 – Süni intellekt əsaslı proqramlaşdırma, Yarımfinal
**Tarix:** 31 oktyabr 2026
**Komanda:** NECİntel · Üzvlər: Sultanova Nazrin Elnur, Abbasov Ashraf Rashid, Shukurlu Javad Maslahat

---

## 1. Həll olunan problem

Bakıda pik saatlarda avtobus marşrutları qeyri-bərabər yüklənir. Gözləmə vaxtı proqnozlaşdırıla bilmir; bəzi xətlərdə avtobuslar boş gedir, digərlərində sərnişinlər dayanacaqda qalır. Mövcud sistemlərdə:

- sərnişin avtobusun **yük səviyyəsini real vaxtda görmür**;
- operator **dispetçer idarəetməsini dinamik tənzimləyə bilmir**, çünki yük haqqında canlı siqnal yoxdur.

Tapşırıq: iki moduldan ibarət funksional prototip — sərnişin modulu (canlı mövqe, ETA, yük hesabatı) və operator modulu + analitika mühərriki (xətt üzrə yük xəritəsi, 10 dəqiqəlik "Yüksək" anomaliyasında "ehtiyat avtobus" tövsiyəsi).

## 2. Həllin icmalı

Sistem crowdsourcing (sərnişin hesabatları) və GPS məlumatını birləşdirən mikrosistemdir. Marşrut şəbəkəsi real məlumatdır: AYNA-nın açıq xəritə API-sindən (map.ayna.gov.az) Bakının 198 marşrutu, ~3800 dayanacağı, hər iki istiqamətin həndəsəsi, rəsmi müddət və daşıyıcı idxal olunub (`app/import_ayna.py`).

**Sərnişin ssenarisi.** Sərnişin marşrutu (axtarışla) və dayanacağı seçir → xəritədə avtobuslar dövlət nömrəsi ilə canlı hərəkət edir → siyahıda növbəti avtobusların ETA-sı, məsafəsi və ara dayanacaq sayı görünür → "Haradan → hara" tabında iki dayanacaq adı yazır: sistem birbaşa marşrutları, gözləmə + yol vaxtını və hər ara dayanacağa vaxtı göstərir, seçilən variant xəritədə çəkilir → sərnişin bir toxunuşla avtobusun yükünü bildirir (Aşağı / Orta / Yüksək) → xəttin yük göstəricisi dərhal yenilənir.

**Operator ssenarisi.** Operator paneli 198 xətti yük səviyyəsinə görə sıralanmış cədvəl və rənglənmiş xəritə kimi göstərir (filtr: yalnız məlumatı olan xətlər), canlı "Son sərnişin hesabatları" lenti və "Marşrut cədvəli" (hər dayanacağa növbəti avtobusun vaxtı, istiqamətlər üzrə) ilə: bal, hesabat sayı (mənbələrə görə), avtobus sayı, orta sürət, GPS əsaslı yığılma (bunching) əlaməti və "Yüksək" seriyasının müddəti. Xətt 10 dəqiqə fasiləsiz "Yüksək" qaldıqda sağ paneldə avtomatik tövsiyə yaranır: **"Ehtiyat əlavə avtobus ayrılmalıdır"**. Operator tövsiyəni qəbul edir; yük düşəndə sistem onu avtomatik bağlayır.

## 3. Funksional tələblərin yerinə yetirilməsi

| # | Tələb (tapşırıqdan) | Status | Harada |
|---|---|---|---|
| 0 | Qeydiyyat / giriş, rollar (sərnişin, operator) | ✔ | `routers/auth.py`, `services/auth.py`, `static/login.html` — e-poçt və ya ad ilə giriş, cookie sessiyası, operator API yalnız operator roluna |
| 1 | Marşrut/dayanacaq seçimində avtobusun canlı mövqeyi | ✔ | `/api/buses`, `/api/routes/{id}`, `static/app.js` (3 s polling, Leaflet markerləri, "Hamısı" rejimi, ən yaxın dayanacaqlar) |
| 2 | Gözlənilən gəliş vaxtı (ETA) | ✔ | `services/eta.py`, `/api/eta` — dövrə üzrə real məsafə / AYNA rəsmi müddətindən çıxarılan orta sürət |
| 2a | Haradan → hara səyahət planı (əlavə) | ✔ | `services/planner.py`, `/api/trip`: top-3 variant, birbaşa və 1 köçürmə ilə, gözləmə + yol, hər dayanacağa vaxt |
| 2c | Seçilmiş avtobusun hər dayanacağa gəliş vaxtı (əlavə) | ✔ | `/api/buses/{id}/timeline` |
| 2d | Mobil tətbiq (PWA), çoxdillilik (az/ru/en) | ✔ | `static/app.html`, `sw.js`, `manifest.webmanifest`, `i18n.js` |
| 2b | Marşrut cədvəli (əlavə) | ✔ | `/api/routes/{id}/timeline`: hər dayanacağa növbəti avtobus |
| 3 | Sərnişin yük hesabatı (aşağı/orta/yüksək) | ✔ | `POST /api/reports`, validasiya (`schemas.py`), UI düymələri |
| 4 | Crowdsourcing + GPS əsasında xətt üzrə yük xəritəsi/siyahısı | ✔ | `services/analytics.py` (çəkili ortalama, bunching), `/api/operator/lines`, `/api/reports/recent` (sərnişin lenti), `static/operator.js` |
| 5 | 10 dəqiqə "Yüksək" → "Ehtiyat əlavə avtobus" tövsiyəsi | ✔ | `AnalyticsEngine.evaluate` + `high_since`, `alerts` cədvəli, operator paneli |
| 6 | İşə salınma: Docker və ya lokal runtime | ✔ | `Dockerfile`, `docker-compose.yml`, README |
| 7 | README: arxitektura axını | ✔ | README "Arxitektura" bölməsi |
| 8 | AI bəyannaməsi | ✔ | `AI_DECLARATION.md` |
| 9 | Texniki izah sənədi | ✔ | bu sənəd |

## 4. Arxitektura

### 4.1 Ümumi axın

```
Sərnişin brauzeri ──┐                         ┌── SQLite ──┐
                    ├─ HTTP/JSON ─► FastAPI ──┤  routes    │
Operator brauzeri ──┘      ▲         │        │  stops     │
                           │         │        │  buses     │
        polling 3–4 s      │         ▼        │  reports   │
                           │   services/      │  line_state│
                           │   analytics ◄────┤  alerts    │
                           │   eta            └────────────┘
                           │   simulator (fon: GPS + virtual sərnişinlər)
                           │   geo
```

### 4.2 Qatlar

| Qat | Fayllar | Məsuliyyət |
|---|---|---|
| Təqdimat | `static/login.html`, `app.html` + `app.js` (mobil PWA, sürüşdürülən alt panel), `operator.html` + `operator.js` (AYNA üslubu), `i18n.js`, `sw.js`, `style.css` | Xəritə (Leaflet + OpenStreetMap), siyahılar, düymələr, polling, 3 dil |
| API | `routers/auth.py`, `routers/passenger.py`, `routers/operator.py`, `schemas.py` | HTTP endpoint-lər, validasiya, 401/403/404/422 cavabları |
| Biznes məntiqi | `services/analytics.py`, `eta.py`, `geo.py`, `simulator.py`, `planner.py`, `auth.py` | Saf hesablama; HTTP-dən asılı deyil; `now` parametri ilə deterministik |
| Məlumat | `db.py`, `seed.py`, `import_ayna.py`, `data/ayna.json` | SQLite sxemi; AYNA-dan 198 real marşrut, ~3800 dayanacaq, ~900 simulyasiya avtobusu |
| Konfiqurasiya | `config.py`, `.env.example` | Pəncərə, anomaliya müddəti, simulyator parametrləri |

### 4.3 Məlumat modeli

- `routes` (AYNA id, nömrə, ad, daşıyıcı, rəng, peak_bias, monitored, dövrə uzunluğu, rəsmi müddət, orta sürət) · `route_points` (dövrə polilaynı: 1-ci + 2-ci istiqamət) · `stops` (AYNA kodu, ad, koordinat) · `route_stops` (istiqamət, dövrə üzrə mövqe, metr)
- `buses` (route_id, dövlət nömrəsi, position_m, speed_kmh, lat, lon, updated_at)
- `reports` (route_id, bus_id?, stop_id?, level, source ∈ {passenger, sim_passenger, demo}, created_at)
- `line_state` (route_id, ts, level, score, report_count) — mühərrikin hər qiymətləndirməsinin izi
- `alerts` (route_id, type, message, status ∈ {active, acknowledged, resolved}, vaxt damğaları)
- `users` (username, email, PBKDF2 şifrə heşi, role, full_name) · `sessions` (token, user_id)

### 4.4 Analitika mühərriki (əsas alqoritmlər)

**Yük səviyyəsi.** Son `LOAD_WINDOW_MINUTES` (10) dəqiqədəki hesabatlar bal alır (low=1, medium=2, high=3) və yeniliyə görə çəkilənir: ən yeni hesabat çəkisi 1.0, pəncərənin sonundakı 0.5; real sərnişin hesabatı (tətbiqdən) virtual hesabatdan 3× ağırdır, ona görə operator sərnişin siqnalını dərhal görür. Çəkili ortalama ≥ 2.5 → "Yüksək", ≥ 1.75 → "Orta", əks halda "Aşağı"; hesabat yoxdursa "Məlumat yoxdur".

**Anomaliya qaydası.** Mühərrik hər 15 saniyədə hər xətt üçün səviyyəni hesablayıb `line_state`-ə yazır. Cari səviyyə "Yüksək" və pəncərədə ≥ `ANOMALY_MIN_REPORTS` (3) hesabat varsa, fasiləsiz "Yüksək" seriyasının başlanğıcı tapılır (`high_since`). Seriya ≥ `ANOMALY_MINUTES` (10) dəqiqədirsə və xətt üçün aktiv tövsiyə yoxdursa, `alerts`-ə "Ehtiyat əlavə avtobus ayrılmalıdır" yazılır. Seriya kəsilərsə sayğac sıfırlanır; yük "Aşağı"/"Məlumat yoxdur" olarsa aktiv tövsiyə avtomatik bağlanır. Minimum hesabat həddi tək bir yanlış hesabatın xəbərdarlıq yaratmasının qarşısını alır.

**GPS göstəriciləri.** Avtobusların xətt üzrə mövqeləri sıralanır; iki avtobus arasındakı məsafə gözlənilən intervalın (xətt uzunluğu / avtobus sayı) 30%-dən azdırsa "yığılma" (bus bunching) işarələnir. Orta sürət də panelə çıxarılır. Real GPS lentində `geo.Polyline.project` koordinatı xətt üzrə mövqeyə çevirir.

**ETA.** Marşrut qapalı dövrədir (1-ci istiqamət + 2-ci istiqamət, AYNA həndəsəsi). Dayanacağa qədər məsafə dövrə üzrə irəli hesablanır (mod L), ETA = məsafə / orta sürət; orta sürət AYNA-nın rəsmi marşrut müddətindən çıxarılır (dövrə uzunluğu / 2×müddət, adətən 16–22 km/s) və dayanacaq gözləmələrini daxil edir. Simulyatorda hərəkət sürəti yükə görə azalır (yüksək yük → 0.7×), beləliklə yük və ETA bir-birinə bağlıdır.

**Səyahət planı (haradan → hara).** Dayanacaqlar adına görə eyniləşdirilir (küçənin iki tərəfi). Birbaşa variantlar: eyni istiqamətdə başlanğıcı sondan əvvəl keçən marşrutlar. Köçürməli variantlar: A marşrutunun başlanğıcdan sonra keçdiyi dayanacaqlar ilə B marşrutunun sona qədər keçdiyi dayanacaqların kəsişməsi; köçürmədə 3 dəqiqə piyada vaxtı və B-nin həmin dayanacağa gəlişdən sonrakı ilk real avtobusu nəzərə alınır (heç biri çatmırsa interval əlavə olunur). Variantlar ümumi vaxta görə sıralanır, ən yaxşı 3-ü qaytarılır.

### 4.5 GPS simulyatoru

Real cihaz olmadığı üçün `GpsSimulator` hər 2 saniyədə ~900 avtobusu real dövrə həndəsəsi üzrə irəlilədir (hər 3.5 km-ə bir avtobus → 10–12 dəqiqəlik interval), dayanacaqda dayandırır, dövrənin sonunda başlanğıca qayıdır. Hər ~6 saniyədə virtual sərnişin hesabatları yaradır; səviyyə paylanması marşrutun `peak_bias` parametrindən asılıdır (5 nömrəli xətt pik meylli → təxminən 10 dəqiqə sonra avtomatik xəbərdarlıq). Simulyator `SIM_ENABLED=0` ilə söndürülə bilər; o zaman sistem yalnız real API məlumatı ilə işləyir.

## 5. Seçilmiş texnologiyalar və səbəblər

| Texnologiya | Səbəb |
|---|---|
| Python 3.12 + FastAPI | Tiplənmiş validasiya (pydantic), avtomatik OpenAPI (`/docs`), asinxron fon tapşırıqları, komanda üçün tanış |
| SQLite (stdlib) | Sıfır konfiqurasiya, Docker həcmi ilə davamlılıq; PostgreSQL-ə keçid üçün `db.py` tək nöqtədir |
| Vanilla JS + Leaflet + OpenStreetMap | Build mərhələsi yoxdur, xəritə pulsuzdur, 4 saatda etibarlı nəticə |
| pytest + httpx TestClient | Biznes məntiqi və API bir əmrlə yoxlanır |
| Docker / docker-compose | Münsif üçün bir əmrlə işə salınma |

## 6. Test strategiyası və etibarlılıq

- **35 avtomatik test** (`pytest`): analitika hədləri və pəncərə; 10 dəqiqəlik qaydanın 9-cu dəqiqədə işləməməsi, 10-cu dəqiqədə işləməsi, kəsilmiş seriyada işləməməsi, az hesabatla işləməməsi, avtomatik bağlanma, qəbul; ETA istiqamət/dönüş məntiqi; polilayn proyeksiyası; simulyatorun hərəkət və dönüş davranışı; AYNA məlumatının idxalı və dövrə qurulması; səyahət planı (birbaşa və köçürmə ilə, köçürmədə gözləmə mənfi olmur) və marşrut/avtobus cədvəli; qeydiyyat (şifrə təkrarı, e-poçt), ad və ya e-poçt ilə giriş, rol əsaslı icazələr (401/403); bütün API endpoint-lərinin müsbət və mənfi halları (404, 422).
- **Validasiya:** səviyyə yalnız `low|medium|high`; avtobus/dayanacaq marşruta aid olmalıdır; mövcud olmayan ID → 404.
- **Dayanıqlılıq:** fon tapşırıqları istisnaları loglayır və dayanmır; DB kilidlə qorunur; `/health` endpoint-i və Docker healthcheck.
- **Təhlükəsizlik:** şifrələr PBKDF2-HMAC-SHA256 (120 000 iterasiya, duz) ilə saxlanılır; sessiya tokeni httpOnly cookie; operator endpoint-ləri rol yoxlaması ilə qorunur; hesabat yalnız daxil olmuş istifadəçidən qəbul edilir.
- **Determinizm:** bütün vaxt-asılı məntiq `now` parametri alır, testlər real saatdan asılı deyil.

## 7. İstifadə rahatlığı

- Sərnişin: mobil tətbiq görünüşü (alt naviqasiya, sürüşdürülən panel, tam ekran xəritə), marşrut axtarışı və "Hamısı" rejimi, ən yaxın 5 dayanacaq, dövlət nömrəsi ilə aydın avtobus adları, izahlı üç böyük düymə, 3 dil, telefona quraşdırma (PWA, iOS/Android).
- Operator: AYNA xəritəsi üslubunda tam ekran xəritə, yığıla bilən panellər, severity üzrə sıralanmış və filtrlənən xətt siyahısı, xətt detalı və dayanacaq cədvəli, xəritədə dayanacağa klik → yaxınlaşan avtobuslar, tövsiyə kartları, canlı sərnişin hesabatları lenti, hadisə jurnalı, **Demo** düyməsi (münsif 10 dəqiqə gözləmir).
- API sənədi `/docs`-da interaktivdir; mobil ekranda tək sütuna keçir.

## 8. Real tətbiq imkanları

- **BakuBus / AYNA** dispetçer mərkəzi üçün: real GPS lenti (hazır cihazlar) `buses` cədvəlinə yazılır, qalan məntiq dəyişmir.
- **Sərnişin tətbiqi** mövcud mobil tətbiqlərə (BakıKart və s.) modul kimi inteqrasiya oluna bilər.
- **Dövlət qurumu** üçün: xətlər üzrə yük tarixçəsi (`line_state`) marşrut şəbəkəsinin planlaşdırılmasında və ehtiyat avtobus parkının ölçülməsində istifadə olunur.

## 9. Gələcək inkişaf

1. Real GPS inteqrasiyası (MQTT/WebSocket), polling əvəzinə SSE/WebSocket.
2. İki köçürməli səyahət planı, piyada hissə (küçə şəbəkəsi), AYNA/GTFS məlumatının avtomatik yenilənməsi; mobil tətbiqin Capacitor ilə App Store / Play Market-ə paketlənməsi; push bildirişlər.
3. ETA üçün ML (tarixi səyahət vaxtları, hava, həftənin günü), yük proqnozu 15–30 dəqiqə irəli.
4. Sərnişin hesabatlarının etibarlılığı: cihaz yaxınlığı ilə təsdiq, istifadəçi reytinqi, anomal hesabatların filtrlənməsi.
5. Operator üçün dispetçer əməliyyatları: ehtiyat avtobusun təyin edilməsi, intervalın dəyişdirilməsi, bildiriş kanalları.
6. PostgreSQL + TimescaleDB, Kubernetes, çox şəhər/operator dəstəyi.

## 10. Komanda və rol bölgüsü

| Üzv | Rol | Məsuliyyət |
|---|---|---|
| Abbasov Ashraf Rashid | Tech lead | Arxitektura, backend, inteqrasiya, demo |
| Shukurlu Javad Maslahat | Builder | Frontend, testlər, validasiya |
| Sultanova Nazrin Elnur | Deliverables owner | Sənədlər, AI jurnalı, işə salınma sınağı, təhvil |
