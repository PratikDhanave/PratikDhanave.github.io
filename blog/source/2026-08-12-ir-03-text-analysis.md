# Text Analysis — Turning Messy Text into Searchable Terms

*Before a single word goes into the index, it passes through a quiet, decisive step: text analysis. Deciding what counts as a "word," how to normalize it, and which words to keep is what lets a search for "running" find a document about "ran," and what makes "The" not clog the index. Get analysis right and search feels intelligent; get it wrong and no clever ranking can save it. This post is about the unglamorous preprocessing that quietly determines search quality.*

Posts 1–2 built the retrieval pipeline and the inverted index. This post is the step that feeds the index: turning raw text into the normalized **terms** that get indexed and matched. It's easy to overlook, but it's where a huge fraction of real search quality is decided — and where the "query and documents must speak the same vocabulary" rule (post 1) is enforced.

## Tokenization: what is a word?

The first step, **tokenization**, breaks a stream of text into individual units (**tokens**, roughly "words"). This sounds trivial and isn't:
- Where are the boundaries? Spaces work for English, mostly — but what about "don't" (one token or two?), "state-of-the-art" (one or four?), "U.S.A." (keep the dots?), or "C++" and "covid-19" (don't lose the symbols)?
- Many languages don't delimit words with spaces at all (Chinese, Japanese), requiring far more sophisticated segmentation.
- Numbers, URLs, emails, and code need special handling or they tokenize into nonsense.

Tokenization decisions directly affect what's findable: if "covid-19" tokenizes to "covid" and "19," a search for the exact term may fail or match spuriously. There's no universally correct tokenizer — it depends on the language and the content — which is why search engines let you configure analysis. The key discipline is consistency: however you tokenize, you must tokenize *queries the same way as documents* (post 1), or they won't match.

## Normalization: collapsing variants to one form

Raw tokens have many surface forms that mean the same thing, and **normalization** collapses them so a search matches regardless of superficial differences:

- **Case folding** — lowercase everything, so "Apple," "apple," and "APPLE" become one term. (Usually right, occasionally wrong — "Apple" the company vs "apple" the fruit — a real trade-off.)
- **Stemming** — chop words to a crude root so related forms collapse: "running," "runs," "ran" → "run"; "organization," "organize," "organizing" → "organ"-ish. Stemming is fast and rule-based (and sometimes over-aggressive, conflating unrelated words), but it's what lets a search for one form find all forms — a major relevance win.
- **Lemmatization** — a smarter, dictionary-and-grammar-based reduction to the true base form ("better" → "good," "ran" → "run"), more accurate than stemming but slower. The choice between stemming and lemmatization is a classic speed/accuracy trade-off.
- **Other normalizations** — removing accents/diacritics, expanding or unifying abbreviations, handling Unicode consistently.

Normalization is what closes much of the vocabulary gap (post 1) at the term level — it's why search feels forgiving of word forms. And again, it must be applied *identically* to documents and queries: if documents are stemmed but queries aren't, they stop matching. The analysis pipeline is a contract both sides must honor.

## Stop words, synonyms, and the judgment in analysis

A few more analysis decisions complete the picture, each a judgment call with real consequences:

- **Stop words** — extremely common words ("the," "is," "of," "a") carry little meaning, appear in nearly every document, and bloat the index with giant postings lists. Historically they were *removed* to save space and speed up queries. Modern engines with better compression and ranking often keep them (they matter for phrases like "to be or not to be" and "The Who"), so stop-word removal is a tunable trade-off between efficiency and precision, not an automatic win.
- **Synonyms** — mapping "car"↔"automobile," "NYC"↔"New York City," so a search for one finds the other, directly attacking the vocabulary gap at indexing or query time. Powerful but risky (wrong synonyms hurt precision), and domain-specific.
- **Language-specific analysis** — stemming rules, tokenization, and stop words are all language-dependent, so multilingual search needs per-language analysis pipelines.

The meta-point is that text analysis is where **domain and language knowledge** enters search, and it's astonishingly high-leverage: the same index and the same ranking function produce dramatically different quality depending on analysis choices. A medical search engine, a code search engine, and a general web engine need very different analysis, and tuning analysis is often where the biggest relevance gains in a search system come from — bigger than tweaking the ranking function. It's also the step that modern **semantic search** (post 7) partly transcends: embeddings capture meaning directly, reducing reliance on stemming and synonyms — but even hybrid systems still analyze text for their keyword half, so analysis remains foundational. The humble preprocessing step is, quietly, one of the most important levers in all of search.

The throughline: before indexing, **text analysis** turns raw text into normalized **terms**, and it quietly decides much of search quality. **Tokenization** (splitting text into tokens) is deceptively hard (punctuation, hyphens, symbols, space-less languages) and directly controls what's findable. **Normalization** collapses surface variants — **case folding**, **stemming** (fast crude roots) vs **lemmatization** (accurate dictionary base forms), accent/Unicode handling — closing the vocabulary gap at the term level. **Stop words** (remove common noise vs keep for phrases — a tunable trade-off) and **synonyms** (map equivalents, powerful but risky) add more judgment, all **language-specific**. The iron rule throughout: analyze **queries exactly as documents** (post 1), or matching breaks. Analysis is where domain/language knowledge enters and is often the highest-leverage lever in search — more than the ranking function.

## Key takeaways

- **Text analysis** converts raw text into the normalized **terms** that get indexed/matched, and it decides a large share of search quality before any ranking happens.
- **Tokenization** (splitting text into tokens/"words") is non-trivial — punctuation, hyphens, symbols ("covid-19," "C++"), and space-less languages all complicate it — and controls what's findable; there's no universal tokenizer, only consistent ones.
- **Normalization** collapses variants to one form: **case folding**, **stemming** (fast, rule-based, crude roots — "running/ran" → "run"; can over-conflate) vs **lemmatization** (dictionary/grammar base forms — more accurate, slower), plus accent/Unicode handling — closing the vocabulary gap at the term level.
- **Stop words** (remove common noise for efficiency vs keep for phrases like "to be or not to be" — a tunable trade-off) and **synonyms** (map "car"↔"automobile" — powerful but precision-risky, domain-specific) add further judgment; all analysis is **language-dependent**.
- The iron rule: analyze **queries identically to documents** (post 1) or matching breaks; analysis is where **domain/language knowledge** enters and is often search's **highest-leverage lever** — bigger relevance gains than tuning ranking — though **semantic search** (post 7) partly transcends it by matching meaning directly.

## Further reading

- [Stemming — reducing words to their root form](https://en.wikipedia.org/wiki/Stemming)
- [Lexical analysis — tokenizing text into terms](https://en.wikipedia.org/wiki/Lexical_analysis)
