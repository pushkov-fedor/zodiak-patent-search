**1. Общие сведения**

API "Поисковая платформа" РОСПАТЕНТ предоставляет программный интерфейс для доступа к патентной информации. Он позволяет осуществлять поиск, получать данные о патентных документах и их метаданные. API основан на Elasticsearch и обратно совместим с ним, что обеспечивает широкий набор поисковых возможностей.

**Адрес API:**

```
https://searchplatform.rospatent.gov.ru/patsearch/v0.2/
```

**2. Безопасность**

Безопасность обеспечивается комбинацией HTTPS и JWT (JSON Web Token). Все запросы к API требуют авторизации с помощью JWT токенов (API ключей), которые выдаются зарегистрированным пользователям в личном кабинете.

**3. Основные возможности API**

*   **Патентный поиск (POST /search):**
    *   Позволяет осуществлять полнотекстовый поиск по базе патентных документов. Использует специализированный язык запросов или запросы на естественном языке.
    *   **Принцип работы:** Поиск документов, содержащих определенные ключевые слова, фразы или комбинации условий в различных полях (заголовок, реферат, описание, формула, классификационные индексы). Результаты фильтруются и сортируются.
    *   **Параметры запроса (в формате JSON):**
        *   `q`: Поисковый запрос на специальном языке (подробности в Приложении 1).
        *   `qn`: Поисковый запрос на естественном языке.
        *   `limit`: Максимальное количество возвращаемых результатов (по умолчанию 10, максимум 10000).
        *   `offset`: Смещение от начала списка результатов (по умолчанию 0).
        *   `pre_tag`, `post_tag`: Теги для подсветки терминов в результатах (по умолчанию `<em>` и `</em>`). Можно передавать массивы тегов для циклической подсветки.
        *   `sort`: Параметр сортировки результатов:
            *   `relevance` (по умолчанию)
            *   `publication_date:asc`
            *   `publication_date:desc`
            *   `filing_date:asc`
            *   `filing_date:desc`
        *   `group_by`: Параметр группировки по патентным семействам:
            *   `family:docdb`
            *   `family:dwpi`
        *   `include_facets`: Флаг включения фасетных данных для фильтрации (1 - включить, 0 - выключить, по умолчанию 0).
        *   `filter`: Фильтр для атрибутивного поиска, используется в связке с `include_facets`.
            *   `authors`: По авторам (`{"values": [<список значений>]}`).
            *   `patent_holders`: По патентообладателям.
            *   `country`: По стране публикации (двухбуквенный код, ST.3).
            *   `kind`: По коду вида документа.
            *   `date_published`: По дате публикации (`{"range": {"gt": "<дата>", "gte": "<дата>", "lt": "<дата>", "lte": "<дата>"}}`).
            *   `application.filing_date`: По дате подачи заявки.
            *   `classification.ipc`: По кодам МПК.
            *   `classification.ipc_group`: По группам МПК.
            *   `classification.ipc_subclass`: По подклассам МПК.
            *   `classification.cpc`: По кодам СПК.
            *   `classification.cpc_group`: По группам СПК.
            *   `classification.cpc_subclass`: По подклассам СПК.
            *   `ids`: Фильтр по идентификаторам документов.
        *   `datasets`: Фильтр по поисковым массивам (`["cis", "ru_since_1994", ...]`).
        *   `highlight`: Параметры детальной подсветки, позволяет задавать несколько профилей подсветки:
            *   `profiles`: Массив профилей подсветки, каждый профиль содержит:
                *   `q`: Выражение на языке запросов.
                *   `pre_tag`: Открывающий тег подсветки.
                *   `post_tag`: Закрывающий тег подсветки.
                *   Можно использовать предопределенный профиль `"_searchquery_"` для ссылки на подсветку поискового запроса.
    *   **Структура ответа (JSON):**
        *   `total`: Общее количество найденных документов.
        *   `available`: Количество доступных документов.
        *   `hits`: Массив документов, где каждый документ содержит:
            *   `common`: Общая информация о документе.
            *   `meta`: Метаданные о источнике документа.
            *   `biblio`: Библиографические данные на разных языках.
            *   `id`: Идентификатор документа.
            *   `index`: Индекс документа.
            *   `dataset`: Поисковый массив документа.
            *   `similarity`: Коэффициент релевантности (относительное значение).
            *   `similarity_norm`: Нормализованный коэффициент релевантности.
            *   `snippet`: Фрагменты текста с подсветкой терминов.

*   **Получение списка поисковых массивов (GET /datasets/tree):**
    *   Возвращает дерево доступных поисковых массивов.
    *   Структура ответа (JSON): массив объектов с информацией о массивах, их типе и названии.

*   **Предоставление данных патентного документа (GET /docs/<идентификатор документа>):**
    *   Возвращает полные данные патентного документа по его идентификатору.
    *   Идентификатор документа формируется как `{код страны публикации}{номер публикации}{код вида документа}_{дата публикации в формате YYYYMMDD}` (для опубликованных документов) или `{код страны подачи заявки}{номер заявки}{код вида документа}_{дата подачи заявки в формате YYYYMMDD}` (для неопубликованных заявок).
    *   Структура ответа (JSON): полные данные патентного документа.

*   **Поиск похожих патентных документов (POST /similar_search):**
    *   Позволяет искать похожие патенты, используя либо идентификатор известного патента, либо фрагмент текста. Использует семантические (векторные) методы поиска.
     *  **Принцип работы:** Поиск документов, концептуально схожих с заданным патентом или текстовым описанием.
    *   **Параметры запроса (в формате JSON):**
        *   `type_search`: Тип поиска ("id_search" или "text_search").
        *   `pat_id`: Идентификатор патента (если `type_search` = "id_search").
        *   `pat_text`: Текст для поиска (если `type_search` = "text_search"). **Важно: текст должен содержать не менее 50 слов.**
        *   `count`: Количество возвращаемых результатов.
    *  **Структура ответа (JSON):**
         *   `total`: Общее количество найденных документов.
        *   `available`: Количество доступных документов.
        *   `hits`: Массив документов, где каждый документ содержит общую информацию, библиографические данные, метаданные, а также фрагменты текста и информацию о релевантности, например:
            ```json
            {
            "common": {
                // ... (общая информация о документе)
            },
            "meta": {
                // ... (метаданные о источнике документа)
            },
            "biblio": {
               // ... (библиографические данные)
            },
            "id": "RU2323344C1_20080427",
            "index": "jun_rupat_new",
            "similarity": 0.0,
            "similarity_norm": 0.0,
            "snippet": {
                // ... (фрагмент текста с подсветкой терминов)
            }
        }
            ```

*   **Предоставление медиаданных патентного документа (GET /media/<путь к файлу>):**
    *   Возвращает медиаданные (изображения, 3D-объекты и т.д.) патентного документа.
    *   `путь к файлу`: `/media/<идентификатор поискового массива>/<кода страны публикации>/<код вида документа>/<дата публикации>/<номер публикации>/<имя файла>`
    *   Структура ответа: Документ в запрошенном формате (например, PDF, изображение).

*   **Классификаторы:**
    *   **Поиск по классификаторам (POST /classification/<идентификатор классификатора>/search):**
         *   `<идентификатор классификатора>`: `ipc` (МПК) или `cpc` (СПК).
        *   Параметры:
           *   `query`: Поисковое выражение на естественном языке.
           *   `lang`: Язык ("ru" или "en").
    *   **Получение информации по коду классификатора (POST /classification/<идентификатор классификатора>/code):**
         *   `<идентификатор классификатора>`: `ipc` (МПК) или `cpc` (СПК).
        *   Параметры:
           *  `code`: Код классификатора.
           *   `lang`: Язык ("ru" или "en").
     *  **Структура ответа:** Список документов, соответствующих запросу.

*   **Коды ответа:**
    *   200 OK: Успешная обработка.
    *   400 Bad Request: Некорректный запрос.
    *   401 Unauthorized: Пользователь не авторизован.
    *   403 Forbidden: Доступ запрещен.
    *   404 Not Found: Запрашиваемый ресурс не найден.
    *   405 Method Not Allowed: Метод не поддерживается.
    *   500 Bad query syntax: Ошибка синтаксиса запроса.
    *   Детализированная информация об ошибке при разборе поисковых выражений будет возвращена в JSON формате.

**4. Сравнение методов `search` и `similar_search`**

| Feature              | `POST /search` (Полнотекстовый поиск)                                        | `POST /similar_search` (Поиск похожих документов)                                                      |
| :------------------- | :----------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- |
| **Назначение**        | Поиск документов на основе **точных критериев**, ключевых слов, фраз, индексов.    | Поиск документов, **похожих по смыслу**, на основе семантического анализа текста или заданного патента. |
| **Язык запросов**     | Специализированный язык запросов (`q`) или запросы на естественном языке (`qn`). |  Фрагмент текста (минимум 50 слов), либо id патента.                               |
| **Метод поиска**    | Полнотекстовый поиск по точным совпадениям и условиям.                    | Семантический поиск по контексту, векторным моделям                                                   |
| **Критерии поиска**   | Определенные ключевые слова, фразы, логические условия, фильтры по полям.         | Семантическая близость, текстовое описание или id патента.                              |
| **Возможности фильтрации** | Фильтрация по различным атрибутам (автор, дата, МПК, и др.).                       | Ограниченные возможности фильтрации (в основном, по количеству документов).  |
| **Возможности сортировки** | Сортировка по релевантности, дате публикации, дате подачи заявки.      | Сортировка по релевантности, на основе семантического сходства.|
| **Когда использовать** | Когда вам нужен **точный** поиск, основанный на конкретных терминах и условиях, с точным соответствием, по отдельным полям, диапазонам и т.д. | Когда у вас есть **текстовое описание** (не менее 50 слов) и вы хотите найти **концептуально похожие** патенты, вне зависимости от конкретных терминов.|

**5. Сценарий поиска**

1) Пользователь API выполняет поиск.
2) Результаты поиска всегда содержат id найденных документов.
3) API всегда возвращает id патентного документа для любых методов, возвращающих какую-либо информацию о патентных документах.
4) Далее полученные id могут использоваться для получения похожих документов.

**6. Поиск релевантных патентов по текстовому описанию**

Для поиска релевантных патентов по текстовому описанию необходимо использовать метод поиска похожих патентных документов по фрагменту текста (POST `/similar_search` с `type_search` равным `"text_search"`).

**Важное требование:** **Текст в поле `pat_text` должен содержать не менее 50 слов.**

**Пример запроса (cURL):**

```bash
curl --location --request POST 'https://searchplatform.rospatent.gov.ru/patsearch/v0.2/similar_search' \
--header 'Authorization: Bearer YOUR_API_KEY' \
--header 'Content-Type: application/json' \
--data-raw '{
  "type_search": "text_search",
  "pat_text": "Предлагаемое изобретение относится к области турбомашиностроения, а именно к конструкции турбореактивных двигателей с камерой сгорания, обеспечивающей эффективное и стабильное горение топлива. Двигатель содержит турбокомпрессор с компрессором, камерой сгорания, выход из которой соединен газовым трактом с турбиной. В компрессор встроен электродвигатель, а в турбину - электрогенератор. Турбина выполнена свободной, что позволяет более гибко управлять процессом работы двигателя. Электрогенератор соединен с электродвигателем посредством силового кабеля, обеспечивая передачу энергии. Обмотки электродвигателя установлены на статоре компрессора. Система постоянных магнитов электродвигателя закреплена на рабочих лопатках компрессора. Обмотки электрогенератора установлены на статоре турбины, а система постоянных магнитов электрогенератора закреплена на рабочих лопатках турбины. Обмотки электродвигателя и электрогенератора заключены в кожуха, к которым подведена система воздушного охлаждения, обеспечивающая необходимый тепловой режим работы. Данная конструкция позволяет повысить эффективность работы двигателя, снизить его габариты и массу, а также улучшить его экологические характеристики.",
  "count": 10
}'
```

**Параметры запроса:**

*   `type_search`: `"text_search"` – указывает, что поиск производится по тексту.
*   `pat_text`: Текст, по которому будет проводиться поиск. **Обязательно должен содержать не менее 50 слов.**
*   `count`: Количество релевантных патентов, которые требуется получить в результате.

**Структура ответа (JSON):**

```json
{
  "total": 2,
  "available": 2,
  "hits": [
    {
      "common": {
        // ... (общая информация о документе)
      },
      "meta": {
        // ... (метаданные о источнике документа)
      },
      "biblio": {
        // ... (библиографические данные)
      },
       "id": "RU2323344C1_20080427",
      "index": "jun_rupat_new",
      "similarity": 0.0,
      "similarity_norm": 0.0,
      "snippet": {
        // ... (фрагмент текста с подсветкой терминов)
      }
    },
       {
      "common": {
        // ... (общая информация о документе)
      },
      "meta": {
        // ... (метаданные о источнике документа)
      },
      "biblio": {
        // ... (библиографические данные)
      },
       "id": "RU2321756C1_20080410",
      "index": "jun_rupat_new",
      "similarity": 0.0,
      "similarity_norm": 0.0,
      "snippet": {
        // ... (фрагмент текста с подсветкой терминов)
      }
    }
  ]
}
```

**7. Приложение 1. Операторы и синтаксис языка запросов**

*   **Логические операторы:** AND, OR, NOT.
*   **Операторы контекстной близости:** WITHIN, ADJ, BETWEEN, +<NUMBER>W, -<NUMBER>W, /<NUMBER>W.
*   **Операторы сравнения (числового поиска):** =, >, <, >=, <=, TO, :.
*   **Усечение и другие операторы подстановки:** \*, ?.
*   **Оператор поиска по фразе:** "".
*   **Оператор нечеткого поиска:** ~.
*   **Скобки:** ().
*   **Сокращения поисковых полей:** `<Сокращение поискового поля>=<Термин/Число/Дата>`.
*   **Использование дат:** Поддерживаются различные форматы даты.
*   **Использование индексов классификаторов:** Поддерживается поиск по индексам МПК, СПК, DWPI и др.
*   **Поиск по числам и диапазонам чисел в тексте**: Поддерживается поиск по числам и диапазонам чисел в полнотекстовых полях с использованием операторов сравнения >, < и TO.

**8. Приложение 2. Формат данных патентного документа**

Данные патентного документа возвращаются в формате JSON и включают поля: `common`, `meta`, `biblio.{lang}`, `abstract.{lang}`, `claims.{lang}`, `description.{lang}`, `drawings`.

