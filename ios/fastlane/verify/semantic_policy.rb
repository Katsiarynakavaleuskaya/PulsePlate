# frozen_string_literal: true

# RU: Общие детерминированные semantic rules для App Store release-ops validation.
# EN: Shared deterministic semantic rules for App Store release-ops validation.
module SemanticPolicy
  APP_STORE_METADATA_FILES = %w[
    name.txt
    description.txt
    subtitle.txt
    promotional_text.txt
    release_notes.txt
    keywords.txt
  ].freeze

  METADATA_MEDICAL_CLAIMS = /
    \b(?:BMI|IMC|medical|doctor(?:s|(?:[-\s]+led))?|diagnos(?:e|es|ed|ing|is|tic)?|patient(?:s)?|prescription(?:s)?|therapy|therapeutic)\b|
    \b(?:ИМТ|медицин(?:а|ский|ская|ские|ских)|врач(?:а|ей|ом)?|диагноз(?:а|ом|е|ы)?|пациент(?:а|ов)?|рецепт(?:а|ов)?|терап(?:ия|ии|ию|ией))\b|
    \b(?:m[eé]dic(?:o|a|os|as|al|amente)?|doctor(?:es)?|diagn[oó]stic(?:o|a|os|as)?|paciente(?:s)?|receta(?:s)?|terapia)\b
  /ix.freeze

  METADATA_TREATMENT_CLAIMS = /
    \b(?:treat(?:ment|ments|s|ed|ing)?|cure(?:s|d|ing)?|heal(?:s|ed|ing)?|prevent(?:s|ed|ing)?)\b|
    \b(?:леч(?:ит|ить|ен|ени(?:е|я))|исцел(?:яет|ение)|профилакт(?:ика|ирует))\b|
    \b(?:tratamient(?:o|os)?|trat(?:a|ar|ado|ando)|cura(?:r|ción|ciones|s)?|san(?:ar|ado|ando)|prev(?:iene|enir|ención))\b
  /ix.freeze

  PROMISSORY_CLAIMS = /
    \b(?:guarantee(?:d|s)?(?:\s+results?)?|instant(?:\s+(?:results?|weight\s+loss|improvement))|rapid(?:\s+(?:results?|weight\s+loss|improvement))|quick(?:\s+(?:results?|weight\s+loss|improvement))|clinically\s+proven(?:\s+results?)?|proven\s+results?)\b|
    \b(?:гарантир(?:ует|уют|ованный|ованные)(?:\s+результат(?:ы|ом)?)?|мгновенн(?:ый|ые|о)\s+результат(?:ы|ом)?|быстр(?:ый|ые|о)\s+результат(?:ы|ом)?|доказанн(?:ый|ые|о)\s+результат(?:ы|ом)?)\b|
    \b(?:garantiza(?:do|dos|da|das)?(?:\s+resultados?)?|resultados?\s+comprobados|resultados?\s+instant[aá]neos?|resultados?\s+r[aá]pidos?)\b
  /ix.freeze

  STORE_TRUTH_CLAIMS = [
    /(?:[$€£¥₽]\s*\d)|(?:\d+\s*(?:USD|EUR|GBP|JPY|RUB))/i,
    /\b(?:free\s+trial|trial\s+period|introductory\s+offer|subscribe\s+now|subscription\s+for\s+\$?\d+|auto-?renew(?:ing|al)?)\b/i,
    /\b(?:monthly\s+subscription|yearly\s+subscription)\b/i,
    /\b(?:пробн(?:ый|ая)\s+период|вводн(?:ое|ая)\s+предложение|подпиш(?:итесь|ись)\s+сейчас|автопродлен(?:ие|ием))\b/i,
    /\b(?:ежемесячн(?:ая|ый)\s+подписка|ежегодн(?:ая|ый)\s+подписка)\b/i,
    /\b(?:prueba\s+gratuita|per[ií]odo\s+de\s+prueba|oferta\s+introductoria|suscr[ií]bete\s+ahora|renovaci[oó]n\s+autom[aá]tica)\b/i,
    /\b(?:suscripci[oó]n\s+mensual|suscripci[oó]n\s+anual)\b/i
  ].freeze

  PRIVACY_ADVISORY_HINTS = [
    {
      pattern: /\b(?:analytics|advertising|ads|third-?party\s+sdk|ad(?:vertising)?\s+tracking|cross-?app\s+tracking|tracking\s+pixels?|аналитик(?:а|и|ой)|реклам(?:а|ы|ный)|seguimiento\s+publicitario|anal[ií]tica|publicidad)\b/i,
      message: "review whether App Privacy answers need updating for analytics/advertising language"
    },
    {
      pattern: /\b(?:personalization|personalized\s+ads|data\s+sharing|share(?:s|d|ing)\s+data|персонализ(?:ация|ированный)|обмен\s+данными|personalizaci[oó]n|compart(?:ir|e|imos)\s+datos)\b/i,
      message: "review whether App Privacy answers need updating for personalization/data-sharing language"
    }
  ].freeze

  WELLNESS_DISCLAIMER_PATTERNS = [
    /does\s+not\s+diagnos(?:e|is)[\s,]*(?:or|,|and)?\s*treat[\s,]*(?:or|,|and)?\s*(?:replace|substitute)\s+professional\s+medical\s+care/i,
    /does\s+not\s+diagnos(?:e|is)[\s,]*(?:or|,|and)?\s*treat(?:\s+medical\s+conditions?)?/i,
    /не\s+ставит\s+диагноз[\s,]*(?:и|,)?\s*не\s+лечит[\s,]*(?:и|,)?\s*не\s+заменяет\s+консультаци(?:ю|и)\s+специалиста/i,
    /не\s+ставит\s+диагноз[\s,]*(?:и|,)?\s*не\s+лечит/i,
    /no\s+diagnostica[\s,]*(?:ni|y|,)?\s*(?:no\s+)?trata[\s,]*(?:ni|y|,)?\s*no\s+sustituye\s+la\s+atenci[oó]n\s+m[eé]dica\s+profesional/i,
    /no\s+diagnostica[\s,]*(?:ni|y|,)?\s*(?:no\s+)?trata(?:\s+afecciones?\s+m[eé]dicas?)?/i
  ].freeze

  REVIEW_NOTE_PRIVACY_CONTRADICTIONS = [
    {
      pattern: /\b(?:write(?:s)?(?:\s+back)?\s+to\s+Health|save(?:s)?\s+to\s+Health|sync(?:s)?(?:\s+back)?\s+to\s+Health|updates?\s+Health\s+data|записыва(?:ет|ют)\s+в\s+Health|сохраня(?:ет|ют)\s+в\s+Health|sincroniza(?:n|r)?\s+de\s+vuelta\s+con\s+Health)\b/i,
      message: "Reviewer notes contradict read-only HealthKit posture"
    },
    {
      pattern: /\b(?:collect(?:s|ed|ing)?\s+Health\s+data|store(?:s|d)?\s+Health\s+data\s+on\s+our\s+servers|собира(?:ет|ют)\s+данные\s+Health|almacena(?:mos|n)?\s+datos\s+de\s+Health\s+en\s+nuestros\s+servidores)\b/i,
      message: "Reviewer notes contradict DATA_NOT_COLLECTED Health posture"
    }
  ].freeze

  module_function

  def metadata_hard_failures(pathname, content)
    return [] unless APP_STORE_METADATA_FILES.include?(pathname.basename.to_s)

    sanitized_content = strip_allowed_wellness_disclaimers(content)
    failures = []
    if sanitized_content.match?(METADATA_MEDICAL_CLAIMS)
      failures << "Blocked medical wording found in #{pathname}"
    end
    if sanitized_content.match?(METADATA_TREATMENT_CLAIMS)
      failures << "Blocked treatment/cure wording found in #{pathname}"
    end
    if sanitized_content.match?(PROMISSORY_CLAIMS)
      failures << "Blocked guaranteed/promissory wording found in #{pathname}"
    end
    if store_truth_claim?(sanitized_content)
      failures << "Blocked StoreKit/App Store truth claim found in #{pathname}"
    end
    failures
  end

  def healthkit_copy_hard_failures(pathname, content)
    sanitized_content = strip_allowed_wellness_disclaimers(content)
    failures = []
    failures << "Blocked medical wording found in #{pathname}" if sanitized_content.match?(METADATA_MEDICAL_CLAIMS)
    failures << "Blocked treatment/cure wording found in #{pathname}" if sanitized_content.match?(METADATA_TREATMENT_CLAIMS)
    failures
  end

  def review_notes_hard_failures(pathname, content, read_only:, data_not_collected:)
    REVIEW_NOTE_PRIVACY_CONTRADICTIONS.each_with_object([]) do |rule, failures|
      next if rule[:message].include?("read-only") && !read_only
      next if rule[:message].include?("DATA_NOT_COLLECTED") && !data_not_collected
      next unless review_note_match_without_negation?(content, rule[:pattern])

      failures << "#{rule[:message]}: #{pathname}"
    end
  end

  def review_notes_advisories(pathname, content)
    PRIVACY_ADVISORY_HINTS.each_with_object([]) do |rule, advisories|
      next unless content.match?(rule[:pattern])

      advisories << advisory_message(pathname, rule[:message])
    end
  end

  def advisory_message(pathname, reason)
    "ADVISORY: #{pathname} :: #{reason}"
  end

  def strip_allowed_wellness_disclaimers(content)
    WELLNESS_DISCLAIMER_PATTERNS.reduce(content.dup) do |sanitized, pattern|
      sanitized.gsub(pattern, "")
    end
  end

  def store_truth_claim?(content)
    STORE_TRUTH_CLAIMS.any? { |pattern| content.match?(pattern) }
  end

  def review_note_match_without_negation?(content, pattern)
    content.to_enum(:scan, pattern).any? do
      match = Regexp.last_match
      !negated_review_note_prefix?(content[0...match.begin(0)])
    end
  end

  def negated_review_note_prefix?(prefix)
    recent_prefix = prefix.downcase[-96..] || prefix.downcase
    recent_prefix.match?(
      /
        (?:
          \b(?:do\s+not|does\s+not|did\s+not|don't|doesn't|never|no\s+longer|никогда)\b
          (?:\W+[[:word:]]+){0,3}\W*\z
          |
          \b(?:no|nunca)\s+se\b(?:\W+[[:word:]]+){0,2}\W*\z
          |
          \bне\b(?:\W+(?:сейчас|уже|больше|будет|будем|буду|станет|станут|может|можем|должен|должна|должны|нужно|следует)){0,2}\W*\z
          |
          \b(?:не|no|nunca)\b\W*\z
        )
      /ix,
    )
  end
end
