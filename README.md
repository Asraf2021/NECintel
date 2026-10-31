# Smart Transit & Crowdsourcing Engine

**Digital Azerbaijan Challenge 2026 – Yarımfinal** · Komanda **NECİntel** (Sultanova Nazrin Elnur, Abbasov Ashraf Rashid, Shukurlu Javad Maslahat) · Bakı avtobus marşrutları üçün canlı mövqe, ETA, crowdsourcing yük məlumatı və operator analitikası.

## Problem və həll

Pik saatlarda Bakı avtobusları qeyri-bərabər yüklənir: bəzi xətlərdə avtobuslar boş gedir, digərlərində sərnişinlər dayanacaqda qalır. Sərnişin yükü görmür, operator isə dispetçer idarəetməsini dinamik tənzimləyə bilmir.

Bu prototip iki moduldan ibarət mikrosistemdir:

| Modul | Nə edir |
|---|---|
| **Sərnişin modulu** (`/app`, mobil PWA tətbiqi) | Marşrut (axtarışla və ya "Hamısı") və dayanacaq seçimi, avtobusların xəritədə canlı mövqeyi (dövlət nömrəsi ilə), ETA, seçilmiş avtobusun hər dayanacağa gəliş vaxtı, **haradan → hara** planlayıcısı (ən yaxşı 3 variant: birbaşa və bir köçürmə ilə, gözləmə + yol vaxtı, hər dayanacağa vaxt), ən yaxın dayanacaqlar, yük hesabatı (Aşağı / Orta / Yüksək), sürüşdürülən alt panel, telefona quraşdırma |
| **Operator modulu və analitika mühərriki** (`/operator`) | AYNA üslubunda tam ekran xəritə, 198 xətt üzrə yük siyahısı (sərnişin hesabatları + GPS), xətt detalı (daşıyıcı, müddət, yük, avtobuslar, dayanacaq cədvəli), xəritədə dayanacağa klik → yaxınlaşan avtobuslar, yığıla bilən panellər, canlı sərnişin hesabatları lenti, avtobus yığılması (bunching), anomaliya xəbərdarlığı: xətt 10 dəqiqə fasiləsiz "Yüksək" olduqda **"Ehtiyat əlavə avtobus ayrılmalıdır"** tövsiyəsi |
| **Giriş və rollar** (`/login`) | Qeydiyyat (ad, e-poçt, şifrə + təkrar, rol: Sərnişin / Operator), giriş istifadəçi adı və ya e-poçt ilə, cookie sessiyası; operator paneli yalnız operator roluna açıqdır |
| **Çoxdillilik** | Hər səhifədə AZ / RU / EN seçimi |

Marşrut və dayanacaq məlumatı **AYNA-nın açıq xəritə API-sindən** (map.ayna.gov.az) idxal olunub: Bakının 198 real marşrutu, ~3800 dayanacaq, hər iki istiqamətin real həndəsəsi, rəsmi marşrut müddəti və daşıyıcı. Real GPS cihazları olmadığı üçün avtobuslar daxili **GPS simulyatoru** ilə bu real xətlər üzrə hərəkət etdirilir. Simulyator həmçinin virtual sərnişin hesabatları yaradır (mənbə `sim_passenger`), real sərnişin hesabatları `passenger` mənbəyi ilə ayrı saxlanılır.

## İşə salınma

### Variant A – Docker (tövsiyə olunur)

```bash
docker compose up --build
```

Brauzerdə: <http://localhost:8000> → giriş səhifəsi. Demo hesablar: **operator / operator123** (operator paneli), **sernisin / sernisin123** (sərnişin tətbiqi). Yeni hesab "Qeydiyyat" ilə açılır. API sənədi: <http://localhost:8000/docs>.

Telefonda: kompüterlə eyni Wi-Fi-da `http://<kompüterin IP-si>:8000` açın, Profil → "Tətbiqi telefona quraşdır" (Android: Chrome; iPhone: Safari → Paylaş → Ana ekrana əlavə et).

### Variant B – lokal Python 3.11+

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Testlər

```bash
pytest
```

35 test: analitika qaydaları, ETA/həndəsə, AYNA məlumatının idxalı, simulyator, autentifikasiya/rollar, səyahət planı (köçürmə ilə) və HTTP API.

### Demo ssenarisi (münsiflər üçün, 2 dəqiqə)

1. `sernisin` ilə daxil olun. Dayanacaq tabında marşrut **5** və dayanacaq seçin: xəritədə avtobuslar hərəkət edir, ən yaxın avtobusun ETA-sı və onun hər dayanacağa gəliş vaxtı görünür. "Hamısı" seçib ən yaxın dayanacağı götürsəniz, bütün marşrutların yaxınlaşan avtobusları bir siyahıda çıxır.
   Marşrut tabında **Neftçilər m/st** → **20-ci Sahə dairəsi** yazın: 3 ən yaxşı variant (köçürmə ilə), gözləmə + yol vaxtı və hər dayanacağa vaxt.
2. "Yüksək" düyməsini 3 dəfə basın. Xəttin yükü dərhal "Yüksək" olur.
3. Başqa brauzer/tabda `operator` ilə daxil olun: hesabatınız dərhal "Son sərnişin hesabatları" lentində görünür, 5 nömrəli xətt siyahının başındadır. Xəttə klikləyin: detal və dayanacaq cədvəli açılır. Xəritədə istənilən dayanacağa klikləyin: yaxınlaşan avtobuslar.
4. 10 dəqiqə gözləməmək üçün xətt detalında **Demo** düyməsini basın: son 11 dəqiqəlik "Yüksək" yük simulyasiya edilir və sağ paneldə **"Ehtiyat əlavə avtobus ayrılmalıdır"** tövsiyəsi yaranır.
5. "Qəbul et" düyməsi ilə operator tövsiyəni bağlayır.

Qeyd: simulyatorda 5 nömrəli xəttin pik meyli yüksəkdir (`peak_bias=0.8`), ona görə heç nə basmasanız da təxminən 10 dəqiqə sonra xəbərdarlıq avtomatik yaranır.

## Arxitektura

```
 Brauzer: sərnişin PWA (/app) · operator paneli (/operator) · giriş (/login)
   │  HTML + vanilla JS + Leaflet (OpenStreetMap), i18n (az/ru/en), service worker
   │  hər 3–4 saniyədə fetch (polling), cookie sessiyası
   ▼
 FastAPI (app/main.py)
   ├─ routers/auth.py        /api/auth/register, /login, /logout, /me  (rollar: passenger, operator)
   ├─ routers/passenger.py   /api/routes, /api/stops(+nearest), /api/buses(+timeline), /api/eta, /api/trip, /api/reports
   ├─ routers/operator.py    /api/operator/lines, /alerts, /history, /demo (yalnız operator)
   ├─ services/planner.py    haradan→hara: birbaşa + 1 köçürmə, top-3
   ├─ services/auth.py       PBKDF2 şifrə heşi, sessiyalar
   ├─ services/analytics.py  yük aqreqasiyası, bunching, 10 dəq anomaliya qaydası
   ├─ services/eta.py        dövrə (2 istiqamət) üzrə məsafə / AYNA orta sürəti
   ├─ import_ayna.py         AYNA açıq API-sindən marşrutların idxalı → app/data/ayna.json
   ├─ services/simulator.py  GPS simulyatoru + virtual sərnişinlər (fon tapşırığı)
   └─ services/geo.py        haversine, polilayn, GPS → xətt üzrə mövqe
   ▼
 SQLite (app/db.py) – routes, stops, buses, reports, line_state, alerts, users, sessions
```

**Məlumat axını.** Sərnişin hesabatı → `reports` cədvəli → analitika mühərriki hər 15 saniyədə hər xətt üçün son 10 dəqiqənin çəkili ortalamasını hesablayır (yeni hesabat daha ağırdır, real sərnişin hesabatı virtual hesabatdan 3× ağırdır) → nəticə `line_state`-ə yazılır → fasiləsiz "high" seriyası ≥ 10 dəqiqə və ≥ 3 hesabat olduqda `alerts`-ə tövsiyə əlavə olunur → operator paneli onu göstərir. Yük düşəndə tövsiyə avtomatik "resolved" olur. GPS simulyatoru hər 2 saniyədə avtobusları irəlilədir; xəttin yükü yüksəkdirsə, sürət azalır və dayanacaqda gözləmə uzanır, bu da ETA-ya təsir edir.

**Niyə belə?** 4 saatlıq prototip üçün xarici asılılığı minimum olan stek seçildi: FastAPI (avtomatik OpenAPI sənədi, tiplənmiş validasiya), SQLite (sıfır konfiqurasiya), vanilla JS + Leaflet (build mərhələsi yoxdur). Bütün hesablama məntiqi `services/` qatındadır və `now` parametrini qəbul edir, ona görə vaxtdan asılı qaydalar deterministik test olunur.

## Layihə strukturu

```
smart-transit/
├── app/
│   ├── main.py            # FastAPI tətbiqi, lifespan, fon tapşırıqları
│   ├── config.py          # Settings (mühit dəyişənləri)
│   ├── db.py              # SQLite sxemi və əlaqə
│   ├── seed.py            # AYNA məlumatından marşrutlar, dayanacaqlar, avtobuslar
│   ├── import_ayna.py     # AYNA açıq API idxal skripti
│   ├── data/ayna.json     # 198 real Bakı marşrutu (idxal nəticəsi)
│   ├── schemas.py         # pydantic modelləri
│   ├── routers/           # auth.py, passenger.py, operator.py
│   ├── services/          # analytics.py, eta.py, geo.py, simulator.py, planner.py, auth.py
│   └── static/            # login.html, app.html (PWA), operator.html, *.js, i18n.js, sw.js, manifest, style.css
├── tests/                 # pytest (35 test)
├── Dockerfile, docker-compose.yml, requirements.txt, .env.example
├── README.md (.docx)          # bu fayl – işə salınma təlimatı və arxitektura qeydi
├── AI_DECLARATION.md (.docx)  # AI istifadəsi bəyannaməsi
└── TEXNIKI_IZAH.md (.docx)    # texniki izah sənədi
```

## Konfiqurasiya

`.env.example` faylına baxın. Əsas parametrlər: `ANOMALY_MINUTES` (default 10), `LOAD_WINDOW_MINUTES` (10), `ANOMALY_MIN_REPORTS` (3), `SIM_ENABLED`, `SIM_REPORTS`, `SEED_ROUTE_LIMIT` (zəif kompüterdə məs. 12 xətt).

Məlumatı yenidən idxal etmək (AYNA API-dən): `python -m app.import_ayna`, sonra `data/transit.db` faylını silin.

## API xülasəsi

| Metod | Yol | Təsvir |
|---|---|---|
| GET | `/api/routes` | Marşrutlar, dayanacaqlar və cari yük |
| GET | `/api/routes/{id}` | Polilayn, dayanacaqlar, avtobuslar |
| GET | `/api/buses?route_id=` | Canlı avtobus mövqeləri |
| GET | `/api/eta?stop_id=&route_id=` | Dayanacağa gəliş vaxtları |
| GET | `/api/trip?from_name=&to_name=` | Haradan → hara: top-3 variant (birbaşa və 1 köçürmə), gözləmə + yol, ara dayanacaqlar |
| GET | `/api/buses/{id}/timeline` | Konkret avtobusun hər dayanacağa gəliş vaxtı |
| GET | `/api/stops/nearest?lat=&lon=` | Ən yaxın dayanacaqlar |
| POST | `/api/auth/register`, `/login`, `/logout` · GET `/me` | Qeydiyyat və giriş (ad və ya e-poçt) |
| GET | `/api/routes/{id}/timeline` | Hər dayanacağa növbəti avtobus (operator cədvəli) |
| GET | `/api/stops?q=` / `/api/stops/names` | Dayanacaq axtarışı |
| GET | `/api/reports/recent?source=passenger` | Son sərnişin hesabatları |
| POST | `/api/reports` | Yük hesabatı `{route_id, level, bus_id?, stop_id?}` |
| GET | `/api/operator/lines` | Xətt üzrə yük, mənbələr, GPS göstəriciləri |
| GET | `/api/operator/alerts?status=` | Xəbərdarlıqlar |
| POST | `/api/operator/alerts/{id}/ack` | Tövsiyənin qəbulu |
| GET | `/api/operator/history/{route_id}` | Yük tarixçəsi |
| POST | `/api/operator/demo/high-load/{route_id}` | Demo: 11 dəqiqəlik "Yüksək" ssenari |

Tam interaktiv sənəd: `/docs`.

## Məhdudiyyətlər və növbəti addımlar

- Avtobus mövqeləri simulyasiyadır; real GPS lenti (MQTT/WebSocket) `buses` cədvəlinə yazılan kimi qalan məntiq dəyişmir.
- Səyahət planlayıcısı birbaşa və bir köçürməli variantları tapır; iki köçürmə və piyada hissə növbəti addımdır.
- Mobil tətbiq PWA-dır (brauzerdən quraşdırılır); App Store / Play Market üçün Capacitor ilə paketləmə növbəti addımdır.
- Sessiya cookie-si HTTP üzərindədir; istehsalda HTTPS və `Secure` bayrağı tələb olunur.
- Polling əvəzinə WebSocket/SSE, SQLite əvəzinə PostgreSQL + TimescaleDB.
- ETA üçün tarixi məlumat əsasında ML modeli, pik saat profilləri.
- Sərnişin hesabatlarında sui-istifadəyə qarşı reytinq/limit, cihaz GPS-i ilə avtobusa avtomatik bağlama.
- Operator üçün dispetçer əmrləri (ehtiyat avtobusun təyin olunması) və bildiriş kanalları (SMS/Telegram).
