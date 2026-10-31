# AI istifadəsi haqqında bəyannamə

**Layihə:** Smart Transit & Crowdsourcing Engine · **Müsabiqə:** Digital Azerbaijan Challenge 2026 – Yarımfinal · **Tarix:** 31 oktyabr 2026

Komanda: **NECİntel** (üzvlər: Sultanova Nazrin Elnur, Abbasov Ashraf Rashid, Shukurlu Javad Maslahat)

## 1. İstifadə olunan alətlər

| Alət | Versiya / mühit | Nə üçün istifadə olundu |
|---|---|---|
| **Claude Code** (Anthropic, Claude Fable 5.1 modeli) | Claude desktop tətbiqi, Code rejimi | Qaydaların təhlili, arxitektura qərarı, backend və frontend kodunun yazılması, testlərin yazılması, sənədlərin hazırlanması, xətaların tapılması |
| Leaflet / OpenStreetMap | CDN | Xəritə (AI deyil, open-source kitabxana; qeyd üçün) |

Başqa AI aləti (Copilot, Cursor, ChatGPT) istifadə olunmayıb.

## 2. AI-nin rolu və insanın rolu

| Mərhələ | AI etdi | İnsan etdi |
|---|---|---|
| Qaydaların öyrənilməsi | PDF-dən qiymətləndirmə meyarlarını, təhvil siyahısını çıxardı, 4 saatlıq plan və rol bölgüsü təklif etdi | Qaydaları verdi, planı təsdiqlədi |
| Tapşırığın təhlili | Tapşırığı tələb siyahısına çevirdi, MVP sərhədini müəyyən etdi | Tapşırığı mətn olaraq ötürdü, nəyin vacib olduğunu təsdiqlədi |
| Arxitektura | FastAPI + SQLite + vanilla JS/Leaflet stekini və `services/` qat bölgüsünü təklif etdi | Stek seçimini komandanın bilik səviyyəsinə görə qəbul etdi |
| Kod | `app/` altındakı bütün modulları, `static/` frontend-i, `Dockerfile`, `docker-compose.yml` yazdı; AYNA xəritə saytında açıq API-ni tapıb (map-api.ayna.gov.az) idxal skriptini yazdı və 198 real marşrutu idxal etdi | Kodu işə saldı, demo ssenarisini yoxladı, real marşrut məlumatının və dayanacaqların olmamasını, avtobus adlarının anlaşılmaz olmasını, ETA-nın qeyri-real görünməsini, sərnişin hesabatının operator panelində görünməməsini qeyd etdi, "haradan → hara" funksiyasını tələb etdi |
| Test | 35 pytest testini yazdı, səhvləri özü aşkar edib düzəltdi | Test nəticələrini yoxladı |
| Sənədlər | README, texniki izah və bu bəyannamənin ilkin mətnini yazdı | Komanda adını, üzvləri əlavə etdi, mətni yoxladı |

## 3. İstifadə olunan promptlar (xronoloji)

1. _(Qaydalar PDF-i əlavə olunaraq)_ «Biz komanda şəklində yarışırıq və yarımfinala keçmişik. İndi sənə şərtləri göndərəcəyəm, sən diqqətlə öyrən və 20+ il təcrübəli mütəxəssis kimi həll et. Lazım olan bütün məlumatı topla, sonra Azərbaycan dilində yaz.»
   → Nəticə: qaydaların təhlili, qiymətləndirmə meyarlarına görə strategiya, vaxt planı, sənəd şablonları.
2. «Tapşırığı upload edə bilmirik, mətn olaraq göndərəcəyik.»
3. _(Tapşırığın tam mətni rus dilində yapışdırıldı: «Smart Transit & Crowdsourcing Engine» — sərnişin modulu (canlı mövqe, ETA, yük hesabatı), operator modulu (yük xəritəsi, 10 dəqiqəlik "Yüksək" anomaliyası), təhvil materialları.)_
   → Nəticə: AI tələb siyahısını çıxardı, arxitekturanı seçdi, layihəni sıfırdan yazdı, testləri işlətdi, xətaları düzəltdi.

4. _(Ekran görüntüləri ilə)_ «1-ci şəkildə Azərbaycanda olan bütün marşrutlar yoxdur, bunu map.ayna.gov.az-dan çəkə bilərsən. 2-ci şəkildə bütün dayanacaqlar yoxdur. İnterfeys user-friendly deyil, r88-b1 nə deməkdir anlamıram. Sərnişin kimi Aşağı/Orta basanda operator panelində görünmür. Gözləmə vaxtı qeyri-realdır. Gələcək üçün: hər iki səhifədə haradan-hara seçəndə hər dayanacağa nə qədər vaxt qaldığını göstərsin.»
   → Nəticə: AYNA açıq API-sindən 198 marşrutun idxalı, dövrə əsaslı həndəsə, dövlət nömrəli avtobus adları, real orta sürətlə ETA, sərnişin hesabatlarına 3× çəki və operator lenti, haradan → hara planlayıcısı, marşrut cədvəli.
5. «Komanda adı və üzvlər: NECİntel, …» → sənədlərə yazıldı.
6. «Qeydiyyat və giriş səhifələri lazımdır, rol seçimi (sərnişin / operator); API və keçid yazılarını yuxarıdan sil; dil seçimi az/ru/en; operator UI AYNA xəritəsi kimi; sərnişin üçün mobil tətbiq; Google Maps kimi 3 ən yaxşı variant köçürmə ilə; seçilmiş marşrut üçün dayanacaq cədvəli.»
   → Nəticə: autentifikasiya və rollar, i18n, PWA mobil tətbiq, köçürməli planlayıcı (`services/planner.py`), AYNA üslubunda operator paneli.
7. «Qeydiyyatdan sonra login səhifəsinə yönəlt, e-mail və şifrə təkrarı əlavə et; niyə xəbərdarlıq yalnız 5-ci marşrutda; dayanacaq siyahısı az; Profil/Hesabat-da xəritəni gizlət; ETA siyahısında “hamısı” variantı.» → düzəldildi, 5-ci marşrut izahı: yalnız o xətt 10 dəqiqə fasiləsiz “Yüksək” qalır.
8. «Axtarışda ən azı 5 ən yaxın dayanacaq və lupa; marşrut siyahısında “Hamısı”; demo hesab yazısını sil.» → düzəldildi (`/api/stops/nearest`).
9. «Operator panelində panellər gizlənsin, xəritədə dayanacağa klik → yaxınlaşan marşrutlar; PWA iOS üçün; alt paneli sürüşdürmək; siyahılar ekrandan çıxmasın; girişdə e-mail və ya ad.» → düzəldildi.
10. «ZIP, testlər, sənədlər və GitHub (NECintel).» → testlər yeniləndi (35), sənədlər yeniləndi, ZIP hazırlandı.

AI-yə verilən texniki göstərişlər (sessiya daxilində AI-nin öz iş planı): «portativ Python mühiti qur», «backend: DB sxemi, seed, GPS simulyatoru, ETA, analitika», «frontend: sərnişin və operator səhifələri», «testlər və Docker», «README, bəyannamə, texniki sənəd».

## 4. AI çıxışının yoxlanılması

- Bütün kod `pytest` ilə yoxlanıldı: 35 test, hamısı keçir (`tests/` qovluğu).
- Tətbiq lokal işə salınaraq hər iki modul brauzerdə əl ilə sınaqdan keçirildi: avtobusların hərəkəti, ETA, hesabat göndərilməsi, demo düyməsi ilə xəbərdarlığın yaranması və qəbulu.
- AI-nin ilk versiyasında üç səhv tapıldı və düzəldildi: (a) testdə ara dayanacaq sayı üçün yanlış gözlənti; (b) eyni saniyədə yazılan iki vəziyyət nümunəsi "Yüksək" seriyasını kəsirdi — `high_since` funksiyasında ən son nümunə həlledici sayılır; (c) canlı sistemdə Demo düyməsi fon mühərrikinin köhnə nümunələri ilə qarışdığı üçün xəbərdarlıq yaratmırdı — demo pəncərəsindəki köhnə nümunələr silinib yenidən hesablanır (bu səhv yalnız brauzerdə əl ilə sınaqda üzə çıxdı, testlər onu tutmurdu).
- Xəritə komponentində gizli/ölçüsü dəyişən konteynerdə zoom səhvi brauzer sınağında aşkar edilib `ResizeObserver` ilə düzəldildi.
- Köçürməli planlayıcıda köçürmədə gözləmə vaxtı mənfi çıxırdı (B marşrutunun avtobusu artıq keçmişdisə) — brauzer sınağında tapıldı, intervalla növbəti dövrə hesablanır, test əlavə olundu.
- Mobil tətbiqdə `#map` CSS seçicisinin üstünlüyü xəritəni tam ekran edirdi — hesablanmış ölçülərlə tapılıb düzəldildi.

## 5. Məhsulun özündə AI

Məhsulun daxilində maşın öyrənməsi modeli yoxdur. Analitika mühərriki şəffaf qaydalara əsaslanır (çəkili ortalama, hədd qaydası, interval analizi). Bu, operator üçün izah oluna bilən qərar deməkdir. Gələcək inkişafda ETA üçün tarixi məlumat əsasında regressiya modeli nəzərdə tutulur (bax TEXNIKI_IZAH.md).

## 6. Etik və təhlükəsizlik qeydləri

- AI-yə heç bir şəxsi məlumat, real sərnişin məlumatı və ya gizli açar ötürülməyib. Marşrut və dayanacaq məlumatı AYNA-nın ictimai xəritə API-sindən (açıq, autentifikasiyasız) alınıb; sərnişin hesabatları və avtobus mövqeləri sintetikdir.
- Kodda gizli açar yoxdur; konfiqurasiya `.env.example` ilə sənədləşdirilib. Şifrələr heşlənir (PBKDF2), demo hesablar yalnız sınaq üçündür.
- Yarışdan əvvəl hazırlanmış kod şablonu istifadə olunmayıb; bütün kod yarış vaxtında, tapşırıq verildikdən sonra yazılıb.
