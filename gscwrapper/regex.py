import re 

# word delimiters used to extract words
QUOTE = r'["«»‘’‚‛“”„‟‹›❮❯⹂〝〞〟＂]'

EXCLAMATION = r'[!¡՜߹᥄‼⁈⁉︕﹗！𖺚𞥞]'

FULL_STOP = r'[.։۔܁܂።᙮᠃᠉⳹⳾⸼。꓿꘎꛳︒﹒．｡𖫵𖺘𛲟𝪈]'

COMMA = r'[,՝،߸፣᠂᠈⸲⸴⹁⹉⹌、꓾꘍꛵︐︑﹐﹑，､𑑍𖺗𝪇]'

BRACKET = (r'[[]{}⁅⁆〈〉❬❭❰❱❲❳❴❵⟦⟧⟨⟩⟪⟫⟬⟭⦃⦄⦇⦈⦉⦊⦋⦌⦍⦎⦏⦐⦑⦒⦓⦔⦕⦖⦗⦘⧼⧽⸂⸃⸄⸅⸉⸊⸌⸍⸜⸝⸢⸣⸤⸥⸦⸧〈〉'
           r'《》「」『』【】〔〕〖〗〘〙〚〛︗︷︸︹︺︻︼︽︾︿﹀﹁﹂﹃﹄﹇﹈'
           r'﹛﹜﹝﹞［］｛｝｢｣]')

COLON = r'[:;؛܃܄܅܆܇܈܉፤፥፦᠄⁏⁝⸵꛴꛶︓︔﹔﹕：；𒑱𒑲𒑳𒑴𝪉𝪊]'

PAREN = r'[()⁽⁾₍₎❨❩❪❫⟮⟯⦅⦆⸨⸩﴾﴿︵︶﹙﹚（）｟｠𝪋]'

APOSTROPHE = r'["\'ʼˮ՚ߴߵ＇"]'

EXCLAMATION_MARK_RAW = r'[!¡՜߹᥄‼⁈⁉︕﹗！𖺚𞥞]'

QUESTION_MARK_RAW = r'[?¿;՞؟፧᥅⁇⁈⁉⳺⳻⸮꘏꛷︖﹖？𑅃𞥟' + r'ʔ‽' + r']'

WORD_DELIM = r'[' + r''.join([x.strip('[]')
                              for x in [QUOTE, EXCLAMATION, QUESTION_MARK_RAW, EXCLAMATION_MARK_RAW,
                                        FULL_STOP, COMMA, BRACKET, COLON,
                                        APOSTROPHE + PAREN]]) + r']'