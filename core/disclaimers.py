"""
Medical and Legal Disclaimers

RU: Медицинские и правовые отказы от ответственности.
EN: Medical and legal disclaimers for nutrition application.

This module contains all medical disclaimers and legal notices that must
be displayed to users to clarify the non-medical nature of the application.
"""

from typing import Literal

# Main medical disclaimer
MEDICAL_DISCLAIMER = {
    "en": (
        "⚠️ IMPORTANT MEDICAL DISCLAIMER ⚠️\n\n"
        "This application is NOT intended for medical diagnosis, treatment, prescription, "
        "or to replace professional medical advice. The information provided is for "
        "educational and informational purposes only.\n\n"
        "ALWAYS CONSULT QUALIFIED HEALTHCARE PROFESSIONALS including:\n"
        "• Registered Dietitians/Nutritionists\n"
        "• Physicians/Doctors\n"
        "• Pediatricians (for children)\n"
        "• Obstetricians/Gynecologists (for pregnancy)\n"
        "• Geriatricians (for elderly)\n"
        "• Sports Medicine Specialists (for athletes)\n\n"
        "Individual nutritional needs vary significantly based on medical history, "
        "medications, health conditions, genetics, and other factors that only "
        "qualified healthcare professionals can properly assess.\n\n"
        "Do not make changes to your diet, supplements, or medical treatment "
        "based solely on this app. Seek professional medical advice before "
        "making any health-related decisions."
    ),
    "ru": (
        "⚠️ ВАЖНЫЙ МЕДИЦИНСКИЙ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ⚠️\n\n"
        "Это приложение НЕ предназначено для медицинской диагностики, лечения, "
        "назначений или замены профессиональной медицинской консультации. "
        "Информация предоставляется только в образовательных и информационных целях.\n\n"
        "ВСЕГДА КОНСУЛЬТИРУЙТЕСЬ С КВАЛИФИЦИРОВАННЫМИ МЕДИЦИНСКИМИ СПЕЦИАЛИСТАМИ:\n"
        "• Диетологи/Нутрициологи\n"
        "• Врачи/Доктора\n"
        "• Педиатры (для детей)\n"
        "• Акушеры-гинекологи (при беременности)\n"
        "• Гериатры (для пожилых)\n"
        "• Специалисты спортивной медицины (для спортсменов)\n\n"
        "Индивидуальные потребности в питании значительно варьируются в зависимости "
        "от медицинской истории, лекарств, состояния здоровья, генетики и других "
        "факторов, которые могут должным образом оценить только квалифицированные "
        "медицинские специалисты.\n\n"
        "Не вносите изменения в свой рацион, добавки или медицинское лечение "
        "основываясь только на этом приложении. Обратитесь за профессиональной "
        "медицинской консультацией перед принятием любых решений, связанных со здоровьем."
    )
}

# Special population disclaimers
SPECIAL_POPULATION_DISCLAIMERS = {
    "pregnancy": {
        "en": (
            "🤰 PREGNANCY NUTRITION DISCLAIMER:\n"
            "Nutritional needs during pregnancy are highly individual and require "
            "professional medical supervision. This app provides general guidance only. "
            "Consult your obstetrician, midwife, or registered dietitian for "
            "personalized prenatal nutrition advice. Some nutrients and foods may "
            "be harmful during pregnancy - always verify safety with your healthcare provider."
        ),
        "ru": (
            "🤰 ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ПО ПИТАНИЮ ВО ВРЕМЯ БЕРЕМЕННОСТИ:\n"
            "Потребности в питании во время беременности очень индивидуальны и требуют "
            "профессионального медицинского наблюдения. Это приложение предоставляет "
            "только общие рекомендации. Консультируйтесь с акушером-гинекологом, "
            "акушеркой или диетологом для персонализированных советов по питанию во "
            "время беременности. Некоторые питательные вещества и продукты могут быть "
            "вредными во время беременности - всегда проверяйте безопасность у своего врача."
        )
    },
    "children": {
        "en": (
            "👶 PEDIATRIC NUTRITION DISCLAIMER:\n"
            "Children's nutritional needs are complex and change rapidly with growth. "
            "This app is NOT suitable for infants under 2 years. For children, "
            "always consult pediatricians, pediatric dietitians, or child nutrition "
            "specialists. Growth patterns, food allergies, and developmental needs "
            "require professional assessment."
        ),
        "ru": (
            "👶 ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ПО ДЕТСКОМУ ПИТАНИЮ:\n"
            "Потребности детей в питании сложны и быстро меняются с ростом. "
            "Это приложение НЕ подходит для младенцев до 2 лет. Для детей всегда "
            "консультируйтесь с педиатрами, детскими диетологами или специалистами "
            "по детскому питанию. Модели роста, пищевые аллергии и потребности "
            "развития требуют профессиональной оценки."
        )
    },
    "elderly": {
        "en": (
            "👴 ELDERLY NUTRITION DISCLAIMER:\n"
            "Nutritional needs in older adults are affected by medications, chronic "
            "conditions, and age-related changes in metabolism and absorption. "
            "Consult geriatricians, registered dietitians, or healthcare providers "
            "familiar with elderly nutrition. Medication-food interactions and "
            "medical conditions require professional evaluation."
        ),
        "ru": (
            "👴 ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ПО ПИТАНИЮ ПОЖИЛЫХ:\n"
            "Потребности в питании у пожилых людей зависят от лекарств, хронических "
            "заболеваний и возрастных изменений в метаболизме и усвоении. "
            "Консультируйтесь с гериатрами, диетологами или медицинскими работниками, "
            "знакомыми с питанием пожилых. Взаимодействие лекарств с пищей и "
            "медицинские состояния требуют профессиональной оценки."
        )
    },
    "athletes": {
        "en": (
            "🏃‍♂️ SPORTS NUTRITION DISCLAIMER:\n"
            "Athletic nutrition needs vary greatly by sport, training phase, body "
            "composition goals, and individual factors. This app provides general "
            "sports nutrition guidelines only. Consult certified sports nutritionists, "
            "sports medicine physicians, or registered dietitians with sports "
            "specialization for personalized athletic nutrition plans."
        ),
        "ru": (
            "🏃‍♂️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ ПО СПОРТИВНОМУ ПИТАНИЮ:\n"
            "Потребности спортсменов в питании сильно варьируются в зависимости от вида "
            "спорта, фазы тренировок, целей композиции тела и индивидуальных факторов. "
            "Это приложение предоставляет только общие рекомендации по спортивному питанию. "
            "Консультируйтесь с сертифицированными спортивными нутрициологами, врачами "
            "спортивной медицины или диетологами со специализацией в спорте для "
            "персонализированных планов спортивного питания."
        )
    }
}

# Legal disclaimer
LEGAL_DISCLAIMER = {
    "en": (
        "📋 LEGAL DISCLAIMER:\n"
        "This application and its content are provided 'as is' without warranties "
        "of any kind. The developers, contributors, and distributors of this "
        "application are not liable for any health consequences, damages, or "
        "injuries that may result from using this application or following its "
        "recommendations. Users assume full responsibility for their health "
        "decisions and should seek professional medical advice."
    ),
    "ru": (
        "📋 ПРАВОВОЙ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ:\n"
        "Это приложение и его содержание предоставляются 'как есть' без каких-либо "
        "гарантий. Разработчики, участники и распространители этого приложения не "
        "несут ответственности за любые последствия для здоровья, ущерб или травмы, "
        "которые могут возникнуть в результате использования этого приложения или "
        "следования его рекомендациям. Пользователи берут на себя полную ответственность "
        "за свои решения о здоровье и должны обращаться за профессиональной медицинской консультацией."
    )
}

# Data privacy disclaimer
PRIVACY_DISCLAIMER = {
    "en": (
        "🔒 PRIVACY NOTICE:\n"
        "This application is designed to be privacy-compliant and does NOT store "
        "personal health information permanently. All calculations are performed "
        "locally and temporarily. However, users should be aware that entering "
        "personal health information carries inherent privacy risks. Only enter "
        "information you are comfortable sharing."
    ),
    "ru": (
        "🔒 УВЕДОМЛЕНИЕ О КОНФИДЕНЦИАЛЬНОСТИ:\n"
        "Это приложение разработано с соблюдением конфиденциальности и НЕ хранит "
        "личную медицинскую информацию постоянно. Все расчеты выполняются локально "
        "и временно. Однако пользователи должны знать, что ввод личной медицинской "
        "информации несет неотъемлемые риски конфиденциальности. Вводите только "
        "информацию, которой вы готовы поделиться."
    )
}

def get_disclaimer_text(disclaimer_type: Literal["medical", "legal", "privacy"],
                       special_population: str = None,
                       language: Literal["en", "ru"] = "en") -> str:
    """
    RU: Получить текст отказа от ответственности.
    EN: Get disclaimer text.

    Args:
        disclaimer_type: Type of disclaimer needed
        special_population: Special population if applicable
        language: Language for disclaimer

    Returns:
        Formatted disclaimer text
    """
    disclaimers = []

    if disclaimer_type == "medical":
        disclaimers.append(MEDICAL_DISCLAIMER[language])

        if special_population and special_population in SPECIAL_POPULATION_DISCLAIMERS:
            disclaimers.append(SPECIAL_POPULATION_DISCLAIMERS[special_population][language])

    elif disclaimer_type == "legal":
        disclaimers.append(LEGAL_DISCLAIMER[language])

    elif disclaimer_type == "privacy":
        disclaimers.append(PRIVACY_DISCLAIMER[language])

    return "\n\n".join(disclaimers)

def get_comprehensive_disclaimer(special_populations: list = None,
                               language: Literal["en", "ru"] = "en") -> str:
    """
    RU: Получить полный отказ от ответственности.
    EN: Get comprehensive disclaimer.
    """
    disclaimers = [
        MEDICAL_DISCLAIMER[language],
        LEGAL_DISCLAIMER[language],
        PRIVACY_DISCLAIMER[language]
    ]

    if special_populations:
        for population in special_populations:
            if population in SPECIAL_POPULATION_DISCLAIMERS:
                disclaimers.append(SPECIAL_POPULATION_DISCLAIMERS[population][language])

    return "\n\n" + "="*50 + "\n\n".join(disclaimers) + "\n" + "="*50

# Professional referral recommendations
PROFESSIONAL_REFERRALS = {
    "general": {
        "en": "Consider consulting: Registered Dietitian, Primary Care Physician",
        "ru": "Рассмотрите консультацию: Диетолог, Врач первичной медицинской помощи"
    },
    "weight_management": {
        "en": "Consider consulting: Registered Dietitian, Endocrinologist, Bariatric Specialist",
        "ru": "Рассмотрите консультацию: Диетолог, Эндокринолог, Бариатрический специалист"
    },
    "sports": {
        "en": "Consider consulting: Sports Nutritionist, Sports Medicine Physician, Registered Dietitian",
        "ru": "Рассмотрите консультацию: Спортивный нутрициолог, Врач спортивной медицины, Диетолог"
    },
    "pediatric": {
        "en": "Consider consulting: Pediatrician, Pediatric Dietitian, Child Development Specialist",
        "ru": "Рассмотрите консультацию: Педиатр, Детский диетолог, Специалист по развитию детей"
    },
    "pregnancy": {
        "en": "Consider consulting: Obstetrician, Midwife, Prenatal Nutritionist, Registered Dietitian",
        "ru": "Рассмотрите консультацию: Акушер-гинеколог, Акушерка, Пренатальный нутрициолог, Диетолог"
    },
    "elderly": {
        "en": "Consider consulting: Geriatrician, Registered Dietitian, Primary Care Physician",
        "ru": "Рассмотрите консультацию: Гериатр, Диетолог, Врач первичной медицинской помощи"
    }
}

def get_professional_referral(category: str, language: Literal["en", "ru"] = "en") -> str:
    """Get professional referral recommendation."""
    return PROFESSIONAL_REFERRALS.get(category, PROFESSIONAL_REFERRALS["general"])[language]
