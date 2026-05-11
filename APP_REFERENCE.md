# 09_zahony: aplikační reference

Tento dokument slouží jako referenční bod pro další práci na aplikaci, hlavně na UI vrstvě.

## 1. Přehled aplikace

- Stack: Django aplikace s jednou hlavní app `home`.
- Doména: evidence zákazníků, typů záhonů a objednávek záhonů.
- Hlavní UI je server-rendered přes Django templates, bez SPA frameworku.
- Jediný vlastní frontend skript je `static/home/js/order_form.js`, který řeší modální okna a dynamiku formuláře nové objednávky.

## 2. Hlavní datové entity

- `Customer`: jméno, příjmení, FB přezdívka, telefon, město, poznámka.
- `RaisedBed`: název, rozměry, výchozí cena, popis, aktivita.
- `Order`: zákazník, datum objednání, datum vyzvednutí, stav, poznámka.
- `OrderItem`: položka objednávky, vazba na záhon, množství, jednotková cena.

Výpočet ceny:

- `Order.total_price` je počítaná vlastnost nad `OrderItem.line_total`.
- Souhrn na stránce nové objednávky se klientsky dopočítává v JS a serverově se počítá i při re-renderu nevalidního formuláře.

## 3. Routing a obrazovky

Hlavní URL jsou v `home/urls.py`:

- `/` -> kalendář zakázek (`HomePageView`)
- `/objednavky/nova/` -> vytvoření objednávky (`OrderCreateView`)
- `/modals/zakaznici/vytvorit/` -> AJAX vytvoření zákazníka
- `/modals/zahony/vytvorit/` -> AJAX vytvoření typu záhonu

Obrazovky:

- `home/templates/home/index.html`: kalendář zakázek po dnech a hodinách.
- `home/templates/home/order_form.html`: formulář nové objednávky s pravým souhrnem a třemi modály.

## 4. UI architektura

### Base layout

- `home/templates/home/base.html` je společný layout.
- Načítá Google Fonts (`Fraunces`, `Manrope`), Bootstrap CSS a vlastní `base.css`.
- Poskytuje bloky `extra_css`, `content`, `extra_js` a `body_class`.
- Navigace je ručně renderovaná a aktivní stav se odvozuje z `request.resolver_match.url_name`.

### CSS vrstvy

- `static/home/css/base.css`: globální proměnné, typografie, navigace, tlačítka, panely, metriky.
- `static/home/css/index.css`: kalendář a jeho responsivní chování.
- `static/home/css/order_form.css`: dvousloupcový layout formuláře, souhrn a seznam položek.
- `static/home/css/modals.css`: vlastní modální vrstva bez Bootstrap JS.

Designový směr:

- Teplá earth-tone paleta.
- Serif pro titulky, sans-serif pro aplikační text.
- Vizuál působí soudržně a má jasný vlastní charakter, není generický.

### JS vrstva

- `static/home/js/order_form.js` se inicializuje pouze na stránce nové objednávky.
- Řeší:
  - otevření a zavření modálů,
  - odeslání modal formulářů přes `fetch`,
  - dynamické přidávání položek objednávky do hidden formsetu,
  - live přepočet souhrnu objednávky,
  - synchronizaci summary panelu s formulářem.

Použitý přístup:

- Server renderuje základní formulář a management form pro inline formset.
- JS funguje jako enhancement nad klasickým Django POST flow.
- Modální create endpointy vrací JSON a okamžitě obohacují selecty ve formuláři.

## 5. Stav UI při revizi

Celkově:

- HTML/CSS/JS vrstva je čitelná a architektonicky dává smysl.
- Soubory jsou rozdělené rozumně podle obrazovek.
- Na malou interní aplikaci je UI struktura nadprůměrně čistá.
- Největší technický dluh je v několika detailech markupu a v jedné bezpečnostní slabině v JS renderingu.

## 6. Ověřené problémy a rizika

### Vysoká priorita

1. Neescapovaný HTML rendering v `order_form.js`

- `renderItems()` skládá karty přes `innerHTML` a do markupu vkládá `item.bedLabel` bez escapování.
- `bedLabel` vzniká z databázových dat (`RaisedBed.__str__()`), takže při nevhodném vstupu může dojít k XSS v rámci interní aplikace.
- Dotčená místa: `itemsSummary.innerHTML` a `summaryItemsList.innerHTML`.

Doporučení:

- Přepsat renderování položek na bezpečnou tvorbu DOM uzlů přes `document.createElement()` a `textContent`.
- Pokud zůstane string rendering, zavést explicitní escape helper.

### Střední priorita

2. Chybná HTML struktura v base layoutu

- V `base.html` je jeden nadbytečný uzavírací tag `</nav>`.
- Browser to pravděpodobně opraví sám, ale markup je formálně nevalidní a komplikuje další úpravy layoutu.

3. Modály nemají dotaženou přístupnost

- Modály mají `role="dialog"` a `aria-modal="true"`, což je dobrý základ.
- Chybí focus trap, navracení focusu na původní trigger a pravděpodobně i zavření klikem mimo dialog je řešené jen backdropem, ne focus managementem.
- Pro interní app to není blocker, ale při dalším rozvoji UI to bude limit.

### Nízká priorita

4. Duplicitní definice layoutu ve `order_form.css`

- `.order-form-layout` a `.order-layout` mají stejná pravidla.
- To není bug, ale je to zbytečná duplicita a časem zvyšuje riziko driftu.

5. Část serverového kontextu existuje hlavně kvůli empty-state togglu

- `item_rows` se v šabloně používá jen pro rozhodnutí, zda skrýt empty-state bloky.
- Samotný seznam položek se stejně renderuje klientsky po načtení stránky.
- Není to chyba, jen místo, kde se dá zjednodušit odpovědnost mezi backendem a frontendem.

## 7. Doporučená optimalizace pro další práci

### První vlna

1. Opravit `base.html` a odstranit nadbytečný `</nav>`.
2. Přepsat render položek objednávky v JS na bezpečný DOM rendering bez `innerHTML`.
3. Sloučit duplicitní layout selektory v `order_form.css`.

### Druhá vlna

1. Z modálů udělat malý znovupoužitelný utility modul.
2. Přidat focus management a klávesovou přístupnost modálů.
3. Oddělit `order_form.js` na malé funkční bloky nebo moduly:
   - modal manager,
   - formset/item manager,
   - summary renderer,
   - AJAX helpers.

### Třetí vlna

1. Sjednotit naming pattern v CSS třídách a zmenšit překryv s Bootstrap terminologií (`button`, `btn`, `form-control`, `form-select`).
2. Zvážit lehkou komponentizaci šablon pro opakující se sekce jako metriky, page heading a form sections.
3. Doplnit vizuální stavy pro loading a submit u modal formulářů.

## 8. Praktické poznámky pro další AI

Při úpravách UI držet tyto zásady:

- Zachovat server-rendered Django přístup, není tu základ pro SPA.
- Neničit existující vizuální směr; současný styl je konzistentní a stojí za zachování.
- Preferovat malé, lokální změny po obrazovkách.
- U `order_form.html` vždy kontrolovat vazbu mezi šablonou, hidden formsetem a `order_form.js`.
- U kalendáře dávat pozor na šířku tabulky a sticky hlavičky/sloupce při mobilních změnách.
- Seznam obrazovek už je zjednodušený na kalendář a vytvoření objednávky.

## 9. Doporučený postup pokračování

Pokud bude další práce zaměřená na UI, nejbezpečnější pořadí je:

1. Nejdřív zpevnit markup a JS bezpečnost.
2. Pak řešit UX modálů a jemné vizuální vylepšení.
3. Nakonec dělat větší layout refaktor nebo komponentizaci.

## 10. Shrnutí pro rychlé převzetí kontextu

- Aplikace je malý Django systém pro evidenci objednávek záhonů.
- UI stojí na `base.html` + dvou hlavních obrazovkách.
- CSS je rozdělené rozumně po stránkách a design je konzistentní.
- Nejkritičtější problém pro frontend je neescapovaný `innerHTML` rendering položek v `order_form.js`.
- Nejviditelnější markup problém je nadbytečný `</nav>` v `base.html`.
- Další práce na UI má dobrý základ a může pokračovat bez většího architektonického zásahu.