/* Çoxdilli interfeys: az / ru / en. Statik mətn üçün data-i18n, dinamik mətn üçün t(key). */
window.I18N = (function () {
  const D = {
    az: {
      hide_panels: "Panelləri gizlət", show_panels: "Panelləri göstər", approaching: "Yaxınlaşan avtobuslar", all_routes: "Hamısı — bütün marşrutlar", all_hint: "Dayanacaq seçin: bu dayanacağa yaxınlaşan bütün marşrutların avtobusları göstəriləcək.", nearest: "Ən yaxın dayanacaqlar", search_stop: "Dayanacaq axtar…", pick_bus_first: "Əvvəlcə siyahıdan avtobus seçin.", email: "E-poçt", password_confirm: "Şifrənin təkrarı", pw_mismatch: "Şifrələr uyğun gəlmir", registered_ok: "Qeydiyyat uğurludur. İndi daxil olun.", show_all: "Bütün yaxınlaşan avtobuslar", show_nearest: "Yalnız ən yaxın", bus_timeline: "Seçilmiş avtobusun dayanacaqlara gəliş vaxtı", no_match: "Uyğun dayanacaq tapılmadı", app_name: "Smart Transit Bakı", login: "Giriş", register: "Qeydiyyat", username: "İstifadəçi adı", username_or_email: "İstifadəçi adı və ya e-poçt", password: "Şifrə",
      full_name: "Ad Soyad", role: "Rol", role_passenger: "Sərnişin", role_operator: "Operator", login_btn: "Daxil ol",
      register_btn: "Qeydiyyatdan keç", demo_accounts: "Demo hesablar", logout: "Çıxış", language: "Dil",
      need_operator: "Bu bölmə yalnız operatorlar üçündür. Operator kimi daxil olun.",
      tab_stop: "Dayanacaq", tab_trip: "Marşrut", tab_report: "Hesabat", tab_profile: "Profil",
      route: "Marşrut", route_search_ph: "nömrə və ya ad: 5, 65, Əhmədli…", stop: "Dayanacaq", choose_stop: "— Dayanacaq seçin —",
      line_load: "Xəttin yükü", eta_title: "Gözlənilən gəliş (ETA)", next_bus: "Növbəti avtobus", after: "Sonrakı",
      arriving: "gəlir", min: "dəq", km: "km", intermediate: "ara dayanacaq", no_buses: "Bu dayanacağa yaxınlaşan avtobus yoxdur.",
      pick_stop: "Dayanacaq seçin.", timeline_title: "Marşrut cədvəli (hər dayanacağa növbəti avtobus)", direction: "İstiqamət",
      dir1: "1-ci istiqamət", dir2: "2-ci istiqamət", avg_speed: "orta sürət",
      from: "Haradan", to: "Hara", from_ph: "məs. 28 May m/st", to_ph: "məs. Neftçilər m/st", find: "Marşrut tap", swap: "⇄",
      both_stops: "Hər iki dayanacağı seçin.", searching: "Axtarılır…", no_trip: "Bu iki dayanacaq arasında marşrut tapılmadı (birbaşa və ya bir köçürmə ilə).",
      found: "variant tapıldı (ən sürətli əvvəl).", direct: "Birbaşa", transfer1: "1 köçürmə", transfer_at: "köçürmə:", wait: "gözləmə",
      ride: "yol", stops_n: "dayanacaq", stops_and_time: "Dayanacaqlar və vaxt", total: "cəmi",
      report_title: "Avtobusun yükü haqqında məlumat verin", which_bus: "Hansı avtobusdasınız? (istəyə bağlı)", whole_route: "— Ümumi marşrut üzrə —",
      low: "Aşağı", medium: "Orta", high: "Yüksək", no_data: "Hesabat yoxdur", low_hint: "boş yer var", medium_hint: "ayaq üstə yer var",
      high_hint: "sıxlıq, minmək çətindir", report_note: "Hesabatlar anonimdir və 10 dəqiqəlik pəncərədə xəttin yük səviyyəsinə təsir edir. Operator paneli onları dərhal görür.",
      thanks: "Təşəkkürlər! Hesabatınız qəbul edildi.", current_load: "xəttin cari yükü", error: "Xəta", bus: "Avtobus", next: "növbəti",
      install: "Tətbiqi telefona quraşdır", install_hint: "Brauzer menyusunda “Ana ekrana əlavə et” seçin.", installed: "Tətbiq quraşdırılıb.",
      reports_n: "hesabat / 10 dəq", no_data_hint: "Son 10 dəqiqədə bu xətt üzrə sərnişin hesabatı yoxdur.",
      op_title: "Operator paneli", lines: "Xətlər", buses: "Avtobus", reports10: "Hesabat / 10 dəq", alerts: "Aktiv xəbərdarlıq",
      only_data: "yalnız məlumatı olan xətlər", line_search_ph: "xətt nömrəsi…", back: "Geri qayıt", carrier: "Daşıyıcı şirkət",
      loop_len: "Dövrə uzunluğu", duration: "Bir istiqamət müddəti", load: "Yük", reports: "Hesabatlar", bus_count: "Avtobus sayı",
      bunching: "Yığılma (GPS)", normal: "normal", bunching_yes: "yığılma var", high_for: "“Yüksək” müddəti", demo: "Demo: 10 dəq “Yüksək”",
      alerts_title: "Xəbərdarlıqlar və tövsiyələr", no_alerts: "Aktiv xəbərdarlıq yoxdur. Bütün xətlər normal rejimdədir.",
      recommend: "Tövsiyə", acked: "Qəbul edilib", resolved: "Bağlanıb", ack_btn: "Qəbul et / avtobus ayrıldı", feed_title: "Son sərnişin hesabatları",
      no_feed: "Hələ sərnişin hesabatı yoxdur.", log_title: "Son hadisələr", sources_hint: "S = sərnişin (tətbiq, 3× çəki), V = virtual sərnişin, D = demo",
      stops_title: "Dayanacaqlar", next_bus_short: "növbəti avtobus", on_route: "marşrut üzrə",
    },
    ru: {
      hide_panels: "Скрыть панели", show_panels: "Показать панели", approaching: "Приближающиеся автобусы", all_routes: "Все — все маршруты", all_hint: "Выберите остановку: покажем автобусы всех маршрутов, приближающиеся к ней.", nearest: "Ближайшие остановки", search_stop: "Найти остановку…", pick_bus_first: "Сначала выберите автобус из списка.", email: "E-mail", password_confirm: "Повтор пароля", pw_mismatch: "Пароли не совпадают", registered_ok: "Регистрация успешна. Теперь войдите.", show_all: "Все приближающиеся автобусы", show_nearest: "Только ближайший", bus_timeline: "Время прибытия выбранного автобуса на остановки", no_match: "Остановка не найдена", app_name: "Smart Transit Баку", login: "Вход", register: "Регистрация", username: "Имя пользователя", username_or_email: "Имя пользователя или e-mail", password: "Пароль",
      full_name: "Имя Фамилия", role: "Роль", role_passenger: "Пассажир", role_operator: "Оператор", login_btn: "Войти",
      register_btn: "Зарегистрироваться", demo_accounts: "Демо-аккаунты", logout: "Выйти", language: "Язык",
      need_operator: "Этот раздел только для операторов. Войдите как оператор.",
      tab_stop: "Остановка", tab_trip: "Маршрут", tab_report: "Отчёт", tab_profile: "Профиль",
      route: "Маршрут", route_search_ph: "номер или название: 5, 65, Ахмедли…", stop: "Остановка", choose_stop: "— Выберите остановку —",
      line_load: "Загрузка линии", eta_title: "Ожидаемое прибытие (ETA)", next_bus: "Следующий автобус", after: "Затем",
      arriving: "подходит", min: "мин", km: "км", intermediate: "промеж. остановок", no_buses: "К этой остановке автобусы не приближаются.",
      pick_stop: "Выберите остановку.", timeline_title: "Расписание маршрута (следующий автобус к каждой остановке)", direction: "Направление",
      dir1: "1-е направление", dir2: "2-е направление", avg_speed: "средняя скорость",
      from: "Откуда", to: "Куда", from_ph: "напр. 28 May m/st", to_ph: "напр. Neftçilər m/st", find: "Найти маршрут", swap: "⇄",
      both_stops: "Выберите обе остановки.", searching: "Поиск…", no_trip: "Маршрут между этими остановками не найден (прямой или с одной пересадкой).",
      found: "вариант(ов) найдено (быстрые первыми).", direct: "Без пересадок", transfer1: "1 пересадка", transfer_at: "пересадка:", wait: "ожидание",
      ride: "в пути", stops_n: "остановок", stops_and_time: "Остановки и время", total: "итого",
      report_title: "Сообщите о загруженности автобуса", which_bus: "В каком вы автобусе? (необязательно)", whole_route: "— По всему маршруту —",
      low: "Низкая", medium: "Средняя", high: "Высокая", no_data: "Нет отчётов", low_hint: "есть свободные места", medium_hint: "есть место стоя",
      high_hint: "давка, трудно войти", report_note: "Отчёты анонимны и влияют на уровень загрузки линии в 10-минутном окне. Оператор видит их сразу.",
      thanks: "Спасибо! Ваш отчёт принят.", current_load: "текущая загрузка линии", error: "Ошибка", bus: "Автобус", next: "следующая",
      install: "Установить приложение на телефон", install_hint: "В меню браузера выберите «Добавить на главный экран».", installed: "Приложение установлено.",
      reports_n: "отчётов / 10 мин", no_data_hint: "За последние 10 минут по этой линии нет отчётов пассажиров.",
      op_title: "Панель оператора", lines: "Линии", buses: "Автобусов", reports10: "Отчётов / 10 мин", alerts: "Активных оповещений",
      only_data: "только линии с данными", line_search_ph: "номер линии…", back: "Назад", carrier: "Перевозчик",
      loop_len: "Длина круга", duration: "Время в одну сторону", load: "Загрузка", reports: "Отчёты", bus_count: "Автобусов",
      bunching: "Скучивание (GPS)", normal: "норма", bunching_yes: "есть скучивание", high_for: "Длительность «Высокая»", demo: "Демо: 10 мин «Высокая»",
      alerts_title: "Оповещения и рекомендации", no_alerts: "Активных оповещений нет. Все линии в норме.",
      recommend: "Рекомендация", acked: "Принято", resolved: "Закрыто", ack_btn: "Принять / автобус выделен", feed_title: "Последние отчёты пассажиров",
      no_feed: "Отчётов пассажиров пока нет.", log_title: "Последние события", sources_hint: "S = пассажир (приложение, вес 3×), V = виртуальный пассажир, D = демо",
      stops_title: "Остановки", next_bus_short: "след. автобус", on_route: "по маршруту",
    },
    en: {
      hide_panels: "Hide panels", show_panels: "Show panels", approaching: "Approaching buses", all_routes: "All — all routes", all_hint: "Choose a stop: buses of all routes approaching it will be shown.", nearest: "Nearest stops", search_stop: "Search stop…", pick_bus_first: "Pick a bus from the list first.", email: "E-mail", password_confirm: "Repeat password", pw_mismatch: "Passwords do not match", registered_ok: "Registration successful. Please sign in.", show_all: "All approaching buses", show_nearest: "Nearest only", bus_timeline: "Selected bus arrival times at stops", no_match: "No matching stop", app_name: "Smart Transit Baku", login: "Sign in", register: "Sign up", username: "Username", username_or_email: "Username or e-mail", password: "Password",
      full_name: "Full name", role: "Role", role_passenger: "Passenger", role_operator: "Operator", login_btn: "Sign in",
      register_btn: "Create account", demo_accounts: "Demo accounts", logout: "Log out", language: "Language",
      need_operator: "This area is for operators only. Sign in as an operator.",
      tab_stop: "Stop", tab_trip: "Trip", tab_report: "Report", tab_profile: "Profile",
      route: "Route", route_search_ph: "number or name: 5, 65, Ahmadli…", stop: "Stop", choose_stop: "— Choose a stop —",
      line_load: "Line load", eta_title: "Expected arrival (ETA)", next_bus: "Next bus", after: "Then",
      arriving: "arriving", min: "min", km: "km", intermediate: "stops in between", no_buses: "No buses approaching this stop.",
      pick_stop: "Choose a stop.", timeline_title: "Route timetable (next bus to each stop)", direction: "Direction",
      dir1: "Direction 1", dir2: "Direction 2", avg_speed: "avg speed",
      from: "From", to: "To", from_ph: "e.g. 28 May m/st", to_ph: "e.g. Neftçilər m/st", find: "Find route", swap: "⇄",
      both_stops: "Choose both stops.", searching: "Searching…", no_trip: "No route found between these stops (direct or with one transfer).",
      found: "option(s) found (fastest first).", direct: "Direct", transfer1: "1 transfer", transfer_at: "transfer at:", wait: "wait",
      ride: "ride", stops_n: "stops", stops_and_time: "Stops and times", total: "total",
      report_title: "Report how crowded the bus is", which_bus: "Which bus are you on? (optional)", whole_route: "— Whole route —",
      low: "Low", medium: "Medium", high: "High", no_data: "No reports", low_hint: "seats available", medium_hint: "standing room",
      high_hint: "crowded, hard to board", report_note: "Reports are anonymous and affect the line load within a 10-minute window. Operators see them immediately.",
      thanks: "Thank you! Your report was received.", current_load: "current line load", error: "Error", bus: "Bus", next: "next",
      install: "Install the app on your phone", install_hint: "Use “Add to Home screen” in your browser menu.", installed: "App installed.",
      reports_n: "reports / 10 min", no_data_hint: "No passenger reports for this line in the last 10 minutes.",
      op_title: "Operator panel", lines: "Lines", buses: "Buses", reports10: "Reports / 10 min", alerts: "Active alerts",
      only_data: "only lines with data", line_search_ph: "line number…", back: "Back", carrier: "Carrier",
      loop_len: "Loop length", duration: "One-way duration", load: "Load", reports: "Reports", bus_count: "Buses",
      bunching: "Bunching (GPS)", normal: "normal", bunching_yes: "bunching", high_for: "“High” duration", demo: "Demo: 10 min “High”",
      alerts_title: "Alerts and recommendations", no_alerts: "No active alerts. All lines are normal.",
      recommend: "Recommendation", acked: "Acknowledged", resolved: "Resolved", ack_btn: "Acknowledge / bus assigned", feed_title: "Latest passenger reports",
      no_feed: "No passenger reports yet.", log_title: "Recent events", sources_hint: "S = passenger (app, 3× weight), V = virtual passenger, D = demo",
      stops_title: "Stops", next_bus_short: "next bus", on_route: "on route",
    },
  };
  let lang = localStorage.getItem("st_lang") || "az";
  if (!D[lang]) lang = "az";
  function t(key) { return (D[lang] && D[lang][key]) || D.az[key] || key; }
  function apply(root) {
    (root || document).querySelectorAll("[data-i18n]").forEach(e => { e.textContent = t(e.dataset.i18n); });
    (root || document).querySelectorAll("[data-i18n-ph]").forEach(e => { e.placeholder = t(e.dataset.i18nPh); });
    (root || document).querySelectorAll("[data-i18n-title]").forEach(e => { e.title = t(e.dataset.i18nTitle); });
    document.documentElement.lang = lang;
    document.querySelectorAll("select.lang").forEach(s => { s.value = lang; });
  }
  function set(l) { if (D[l]) { lang = l; localStorage.setItem("st_lang", l); apply(); document.dispatchEvent(new Event("langchange")); } }
  function mount() {
    document.querySelectorAll("select.lang").forEach(s => {
      s.innerHTML = '<option value="az">AZ</option><option value="ru">RU</option><option value="en">EN</option>';
      s.value = lang; s.addEventListener("change", () => set(s.value));
    });
    apply();
  }
  return { t, apply, set, mount, get lang() { return lang; } };
})();
window.t = window.I18N.t;
