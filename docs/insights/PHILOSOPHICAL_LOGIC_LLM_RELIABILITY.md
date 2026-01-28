# Philosophical Logic Principles for LLM Reliability

**Document Purpose:** Apply classical Aristotelian logic, analytical philosophy, post-analytical philosophy, and linguistic philosophy principles to improve LLM response reliability and argumentative rigor.

**Status:** Analysis & Design Document
**Created:** 2026-01-28
**Related:** `docs/analysis/LLM_RAG_AI_ASSISTANT_ANALYSIS.md`, `core/insight/creative_scientific_innovations.md`

---

## Executive Summary

This document explores how principles from four philosophical traditions can enhance LLM reliability:

1. **Classical Aristotelian Logic** → Structured reasoning, syllogisms, categorical logic
2. **Analytical Philosophy** → Verification, falsification, logical positivism
3. **Post-Analytical Philosophy** → Contextual interpretation, pragmatism, hermeneutics
4. **Linguistic Philosophy** → Meaning-as-use, speech acts, language games

**Key Insight:** LLMs generate text probabilistically, not logically. By applying philosophical frameworks, we can:
- Structure prompts to enforce logical forms
- Validate outputs against logical rules
- Distinguish factual claims from interpretations
- Improve argumentative coherence

---

## 1. Classical Aristotelian Logic

### Core Principles

**Aristotelian Logic** (Organon, Categories, Prior Analytics):
- **Syllogisms:** Major premise → Minor premise → Conclusion
- **Categorical Logic:** Universal/particular, affirmative/negative
- **Law of Non-Contradiction:** A statement cannot be both true and false
- **Law of Excluded Middle:** A statement is either true or false (no third option)

### Application to LLM Prompts

#### 1.1 Syllogistic Prompt Structure

**Problem:** LLMs generate unstructured arguments without explicit premises.

**Solution:** Enforce syllogistic structure in prompts.

```python
# core/insight/aristotelian_prompts.py
class SyllogisticPromptBuilder:
    """Build prompts that enforce Aristotelian syllogistic structure."""

    def build_syllogistic_prompt(self, query: str, domain: str) -> str:
        """Build prompt with explicit major/minor premise structure."""
        return f"""
You are a logical reasoning assistant. Structure your answer as a valid syllogism:

MAJOR PREMISE (Universal rule): [General principle from {domain}]
MINOR PREMISE (Particular case): [Specific fact about the user's query]
CONCLUSION (Logical inference): [Deduced answer]

Query: {query}

Requirements:
- Major premise must be a general rule (e.g., "All mammals are warm-blooded")
- Minor premise must connect query to major premise
- Conclusion must follow logically from premises
- If premises are uncertain, state uncertainty explicitly
"""

    def validate_syllogism(self, response: str) -> SyllogismValidation:
        """Validate that response follows syllogistic structure."""
        # Extract major/minor/conclusion using regex/NLP
        major = self._extract_major_premise(response)
        minor = self._extract_minor_premise(response)
        conclusion = self._extract_conclusion(response)

        # Check logical validity
        is_valid = self._check_syllogistic_validity(major, minor, conclusion)

        return SyllogismValidation(
            valid=is_valid,
            major_premise=major,
            minor_premise=minor,
            conclusion=conclusion,
            form=self._identify_syllogistic_form(major, minor, conclusion)
        )
```

**Example Prompt:**
```
Query: "Is a BMI of 25.5 considered overweight?"

MAJOR PREMISE: According to WHO guidelines, BMI 25.0-29.9 is classified as overweight.
MINOR PREMISE: The user's BMI is 25.5.
CONCLUSION: Therefore, a BMI of 25.5 is classified as overweight.
```

#### 1.2 Categorical Logic Validation

**Problem:** LLMs mix universal claims ("all X are Y") with particular claims ("some X are Y") without distinction.

**Solution:** Enforce categorical distinctions.

```python
# core/insight/categorical_validator.py
from enum import Enum

class CategoricalType(Enum):
    UNIVERSAL_AFFIRMATIVE = "All S are P"  # A-type
    UNIVERSAL_NEGATIVE = "No S are P"     # E-type
    PARTICULAR_AFFIRMATIVE = "Some S are P"  # I-type
    PARTICULAR_NEGATIVE = "Some S are not P"  # O-type

class CategoricalValidator:
    """Validate categorical statements in LLM responses."""

    def extract_categorical_statements(self, text: str) -> List[CategoricalStatement]:
        """Extract and classify categorical statements."""
        statements = []
        # Pattern matching for "all", "some", "no", "none"
        # Classify as A/E/I/O type
        return statements

    def check_contradiction(self, stmt1: CategoricalStatement, stmt2: CategoricalStatement) -> bool:
        """Check if two statements contradict (A vs O, E vs I)."""
        # A contradicts O, E contradicts I
        if (stmt1.type == CategoricalType.UNIVERSAL_AFFIRMATIVE and
            stmt2.type == CategoricalType.PARTICULAR_NEGATIVE):
            return self._same_terms(stmt1, stmt2)
        # ... other contradiction checks
        return False
```

**Integration:**
```python
# Post-generation validation
categorical_validator = CategoricalValidator()
statements = categorical_validator.extract_categorical_statements(response)

# Check for contradictions
for i, stmt1 in enumerate(statements):
    for stmt2 in statements[i+1:]:
        if categorical_validator.check_contradiction(stmt1, stmt2):
            return ValidationResult(
                valid=False,
                reason=f"Contradiction detected: {stmt1} contradicts {stmt2}"
            )
```

#### 1.3 Law of Non-Contradiction Enforcement

**Problem:** LLMs can generate contradictory statements in the same response.

**Solution:** Post-generation contradiction detection.

```python
# core/insight/non_contradiction.py
class NonContradictionChecker:
    """Enforce Law of Non-Contradiction in LLM responses."""

    def check_contradictions(self, response: str) -> List[Contradiction]:
        """Detect contradictory statements."""
        contradictions = []

        # Extract factual claims
        claims = self._extract_claims(response)

        # Check pairwise contradictions
        for i, claim1 in enumerate(claims):
            for claim2 in claims[i+1:]:
                if self._are_contradictory(claim1, claim2):
                    contradictions.append(Contradiction(
                        claim1=claim1,
                        claim2=claim2,
                        position1=self._find_position(claim1, response),
                        position2=self._find_position(claim2, response)
                    ))

        return contradictions

    def _are_contradictory(self, claim1: str, claim2: str) -> bool:
        """Check if two claims contradict (A and not-A)."""
        # Use semantic similarity + negation detection
        # e.g., "BMI 25 is overweight" vs "BMI 25 is not overweight"
        return self._semantic_contradiction(claim1, claim2)
```

**Usage:**
```python
# In validation pipeline
contradictions = non_contradiction_checker.check_contradictions(response)
if contradictions:
    return ValidationResult(
        valid=False,
        reason=f"Contradictions detected: {contradictions}",
        contradictions=contradictions
    )
```

---

## 2. Analytical Philosophy

### Core Principles

**Analytical Philosophy** (Logical Positivism, Verificationism, Falsificationism):
- **Verification Principle:** A statement is meaningful only if it can be verified empirically
- **Falsificationism (Popper):** Scientific claims must be falsifiable
- **Logical Positivism:** Distinguish between analytical (logical) and synthetic (empirical) statements

### Application to LLM Reliability

#### 2.1 Verification Principle

**Problem:** LLMs generate unverifiable claims (e.g., "this diet is best for everyone").

**Solution:** Require verifiable claims with evidence sources.

```python
# core/insight/verification_principle.py
class VerificationEnforcer:
    """Enforce verification principle: claims must be verifiable."""

    def build_verification_prompt(self, query: str) -> str:
        """Build prompt requiring verifiable claims."""
        return f"""
Answer the following query, but follow the Verification Principle:

VERIFICATION PRINCIPLE: Every factual claim must be:
1. Verifiable (can be checked against evidence)
2. Supported by sources (cite authoritative sources)
3. Falsifiable (can be proven wrong)

For each claim you make:
- State the claim explicitly
- Provide evidence source (USDA, WHO, peer-reviewed study, etc.)
- Indicate if claim is verifiable or speculative

Query: {query}

Response format:
CLAIM 1: [Factual statement]
EVIDENCE: [Source that verifies this claim]
VERIFIABLE: Yes/No
SPECULATIVE: Yes/No (if not verifiable, mark as speculative)

CLAIM 2: ...
"""

    def validate_verifiability(self, response: str) -> VerificationResult:
        """Check if all claims are verifiable."""
        claims = self._extract_claims(response)
        verified = []
        unverified = []

        for claim in claims:
            has_source = self._has_evidence_source(claim)
            is_verifiable = self._is_empirically_verifiable(claim)

            if has_source and is_verifiable:
                verified.append(claim)
            else:
                unverified.append(claim)

        return VerificationResult(
            verified_claims=verified,
            unverified_claims=unverified,
            verification_rate=len(verified) / len(claims) if claims else 0.0
        )
```

**Example:**
```
Query: "What is the recommended daily protein intake?"

CLAIM 1: The RDA for protein is 0.8g per kg body weight per day.
EVIDENCE: USDA Dietary Guidelines 2020-2025, NASM Nutrition Essentials
VERIFIABLE: Yes
SPECULATIVE: No

CLAIM 2: Higher protein (1.2-1.6g/kg) may benefit muscle building.
EVIDENCE: Meta-analysis (Schoenfeld et al., 2018)
VERIFIABLE: Yes (can be tested in controlled studies)
SPECULATIVE: No
```

#### 2.2 Falsificationism (Popper)

**Problem:** LLMs generate unfalsifiable claims (e.g., "this works for some people").

**Solution:** Require falsifiable predictions.

```python
# core/insight/falsification.py
class FalsificationChecker:
    """Apply Popper's falsificationism: claims must be falsifiable."""

    def check_falsifiability(self, claim: str) -> FalsifiabilityResult:
        """Check if a claim is falsifiable."""
        # Unfalsifiable patterns:
        # - "This works for some people" (too vague)
        # - "This is generally good" (no testable criteria)
        # - "This may help" (no falsification condition)

        is_falsifiable = self._has_testable_condition(claim)
        falsification_condition = self._extract_falsification_condition(claim) if is_falsifiable else None

        return FalsifiabilityResult(
            falsifiable=is_falsifiable,
            falsification_condition=falsification_condition,
            claim=claim
        )

    def build_falsifiable_prompt(self, query: str) -> str:
        """Build prompt requiring falsifiable claims."""
        return f"""
Answer the following query, but ensure all claims are FALSIFIABLE:

FALSIFIABILITY PRINCIPLE (Popper): A claim is scientific only if it can be proven wrong.

For each claim:
- State what would prove it wrong (falsification condition)
- Avoid vague claims like "this works for some people"
- Use specific, testable criteria

Query: {query}

Response format:
CLAIM: [Specific, testable statement]
FALSIFICATION CONDITION: [What would prove this claim wrong]
TESTABLE: Yes/No
"""

    def filter_unfalsifiable(self, response: str) -> FilteredResponse:
        """Remove unfalsifiable claims from response."""
        claims = self._extract_claims(response)
        falsifiable_claims = []
        unfalsifiable_claims = []

        for claim in claims:
            result = self.check_falsifiability(claim)
            if result.falsifiable:
                falsifiable_claims.append(claim)
            else:
                unfalsifiable_claims.append(claim)

        return FilteredResponse(
            filtered_response=self._reconstruct_response(falsifiable_claims),
            removed_claims=unfalsifiable_claims
        )
```

**Example:**
```
CLAIM: "A calorie deficit of 500 kcal/day leads to 0.5 kg weight loss per week."
FALSIFICATION CONDITION: "If a person maintains a 500 kcal/day deficit but loses less than 0.4 kg/week over 4 weeks, the claim is falsified."
TESTABLE: Yes (can be tested in controlled studies)
```

#### 2.3 Analytical vs Synthetic Distinction

**Problem:** LLMs mix analytical (logical) statements with synthetic (empirical) statements.

**Solution:** Classify statements and validate accordingly.

```python
# core/insight/analytical_synthetic.py
class AnalyticalSyntheticClassifier:
    """Distinguish analytical (logical) from synthetic (empirical) statements."""

    def classify_statement(self, statement: str) -> StatementType:
        """Classify as analytical or synthetic."""
        # Analytical: true by definition (e.g., "All bachelors are unmarried")
        # Synthetic: requires empirical verification (e.g., "BMI 25 is overweight")

        if self._is_analytical(statement):
            return StatementType.ANALYTICAL
        elif self._is_synthetic(statement):
            return StatementType.SYNTHETIC
        else:
            return StatementType.UNKNOWN

    def _is_analytical(self, statement: str) -> bool:
        """Check if statement is true by definition."""
        # Patterns: "X is defined as Y", "By definition, X is Y"
        # e.g., "BMI is weight divided by height squared" (definitional)
        return self._matches_definitional_pattern(statement)

    def _is_synthetic(self, statement: str) -> bool:
        """Check if statement requires empirical verification."""
        # Patterns: factual claims about the world
        # e.g., "BMI 25 is overweight" (requires WHO guidelines to verify)
        return self._requires_empirical_check(statement)

    def validate_by_type(self, statement: str, statement_type: StatementType) -> ValidationResult:
        """Validate statement according to its type."""
        if statement_type == StatementType.ANALYTICAL:
            # Analytical: check logical consistency
            return self._validate_logical_consistency(statement)
        elif statement_type == StatementType.SYNTHETIC:
            # Synthetic: check against empirical sources
            return self._validate_empirical_claim(statement)
        else:
            return ValidationResult(valid=False, reason="Unknown statement type")
```

---

## 3. Post-Analytical Philosophy

### Core Principles

**Post-Analytical Philosophy** (Pragmatism, Hermeneutics, Contextualism):
- **Pragmatism (Dewey, Rorty):** Truth is what works in practice
- **Hermeneutics (Gadamer):** Understanding requires interpretation within context
- **Contextualism:** Meaning depends on context

### Application to LLM Reliability

#### 3.1 Pragmatic Validation

**Problem:** LLMs generate theoretically correct but practically useless answers.

**Solution:** Validate answers against practical utility.

```python
# core/insight/pragmatic_validator.py
class PragmaticValidator:
    """Apply pragmatic principle: truth is what works in practice."""

    def validate_practical_utility(self, response: str, user_context: UserContext) -> PragmaticResult:
        """Check if response is practically useful."""
        # Criteria:
        # 1. Actionable (user can act on it)
        # 2. Contextually relevant (fits user's situation)
        # 3. Testable (user can verify if it works)

        is_actionable = self._has_actionable_steps(response)
        is_contextually_relevant = self._matches_user_context(response, user_context)
        is_testable = self._has_testable_outcome(response)

        return PragmaticResult(
            practically_useful=is_actionable and is_contextually_relevant and is_testable,
            actionable=is_actionable,
            contextually_relevant=is_contextually_relevant,
            testable=is_testable
        )

    def build_pragmatic_prompt(self, query: str, user_context: UserContext) -> str:
        """Build prompt emphasizing practical utility."""
        return f"""
Answer the following query with PRACTICAL UTILITY in mind:

PRAGMATIC PRINCIPLE: A good answer is one that works in practice, not just theoretically correct.

User context:
- Age: {user_context.age}
- Goals: {user_context.goals}
- Constraints: {user_context.constraints}

Requirements:
1. Provide actionable steps (what user can do)
2. Consider user's context (age, goals, constraints)
3. Include testable outcomes (how user knows it works)
4. Avoid purely theoretical answers

Query: {query}
"""
```

**Example:**
```
Query: "How can I lose weight?"

BAD (theoretical): "Weight loss requires a calorie deficit, which can be achieved through diet and exercise."

GOOD (pragmatic):
"Based on your age (30) and goal (lose 5 kg in 3 months):
1. Calculate your TDEE: [link to calculator]
2. Create a 500 kcal/day deficit: [specific meal plan]
3. Track daily: [app recommendation]
4. Test outcome: Weigh weekly; if no loss after 2 weeks, adjust deficit"
```

#### 3.2 Hermeneutic Context Integration

**Problem:** LLMs ignore user context, giving generic answers.

**Solution:** Integrate hermeneutic interpretation (understanding within context).

```python
# core/insight/hermeneutic_interpreter.py
class HermeneuticInterpreter:
    """Apply hermeneutic principle: understanding requires context."""

    def build_contextual_prompt(self, query: str, user_history: List[Interaction]) -> str:
        """Build prompt with full hermeneutic context."""
        # Hermeneutic circle: part (query) understood through whole (context)
        context_summary = self._summarize_user_history(user_history)

        return f"""
Interpret this query within its FULL CONTEXT:

HERMENEUTIC PRINCIPLE: Understanding requires interpreting parts (query) within whole (user's history/goals).

User's previous interactions:
{context_summary}

Current query: {query}

Requirements:
1. Interpret query in light of user's history
2. Identify implicit assumptions (what user likely means)
3. Connect to user's ongoing goals/concerns
4. Provide contextually coherent answer (not generic)
"""
```

**Example:**
```
User history: Previously asked about BMI calculation, mentioned goal to lose weight.
Current query: "What should I eat?"

HERMENEUTIC INTERPRETATION:
- Implicit: User wants meal plan for weight loss (not general nutrition)
- Context: User calculated BMI, likely overweight/obese
- Answer: Focus on calorie deficit meal plan, not general healthy eating
```

#### 3.3 Contextual Meaning Resolution

**Problem:** LLMs misinterpret ambiguous queries due to missing context.

**Solution:** Resolve meaning through context (linguistic philosophy principle).

```python
# core/insight/contextual_resolver.py
class ContextualResolver:
    """Resolve meaning through context (Wittgenstein: meaning-as-use)."""

    def resolve_meaning(self, query: str, context: ConversationContext) -> ResolvedQuery:
        """Resolve ambiguous query through context."""
        # Meaning-as-use: meaning comes from how language is used in context

        ambiguous_terms = self._find_ambiguous_terms(query)
        resolved_meanings = {}

        for term in ambiguous_terms:
            # Resolve through context (previous uses, user's goals)
            resolved_meanings[term] = self._resolve_term_from_context(term, context)

        return ResolvedQuery(
            original_query=query,
            resolved_query=self._substitute_resolved_terms(query, resolved_meanings),
            ambiguity_resolutions=resolved_meanings
        )
```

**Example:**
```
Query: "Is this good?"
Context: Previous message about "keto diet"

RESOLVED: "Is the keto diet good for my weight loss goal?"
(Resolved "this" → "keto diet", "good" → "good for weight loss")
```

---

## 4. Linguistic Philosophy

### Core Principles

**Linguistic Philosophy** (Wittgenstein, Austin, Searle):
- **Meaning-as-Use (Wittgenstein):** Meaning comes from how words are used, not definitions
- **Speech Acts (Austin):** Utterances perform actions (assertions, questions, commands)
- **Language Games:** Meaning depends on the "game" (context/activity)

### Application to LLM Reliability

#### 4.1 Speech Act Classification

**Problem:** LLMs treat all queries as assertions, missing implicit speech acts.

**Solution:** Classify speech acts and respond appropriately.

```python
# core/insight/speech_acts.py
from enum import Enum

class SpeechActType(Enum):
    ASSERTION = "assertion"  # "BMI 25 is overweight"
    QUESTION = "question"     # "Is BMI 25 overweight?"
    COMMAND = "command"       # "Calculate my BMI"
    REQUEST = "request"       # "Please explain BMI categories"
    EXPRESSION = "expression" # "I'm worried about my weight"

class SpeechActClassifier:
    """Classify speech acts in user queries."""

    def classify_speech_act(self, query: str) -> SpeechActType:
        """Classify the speech act performed by query."""
        # Patterns:
        # Question: "Is...?", "What...?", "How...?"
        # Command: "Calculate...", "Show me...", "Give me..."
        # Request: "Please...", "Could you...?"
        # Expression: "I feel...", "I'm worried..."

        if self._is_question(query):
            return SpeechActType.QUESTION
        elif self._is_command(query):
            return SpeechActType.COMMAND
        elif self._is_request(query):
            return SpeechActType.REQUEST
        elif self._is_expression(query):
            return SpeechActType.EXPRESSION
        else:
            return SpeechActType.ASSERTION

    def build_speech_act_prompt(self, query: str, speech_act: SpeechActType) -> str:
        """Build prompt appropriate for speech act type."""
        if speech_act == SpeechActType.QUESTION:
            return f"""
This is a QUESTION. Answer directly and factually.

Query: {query}

Requirements:
- Direct answer (not "it depends")
- Cite sources
- If uncertain, state uncertainty explicitly
"""
        elif speech_act == SpeechActType.COMMAND:
            return f"""
This is a COMMAND. Perform the requested action.

Query: {query}

Requirements:
- Execute the command (calculate, show, etc.)
- Provide result immediately
- Include explanation if needed
"""
        elif speech_act == SpeechActType.REQUEST:
            return f"""
This is a REQUEST. Provide helpful information.

Query: {query}

Requirements:
- Be helpful and detailed
- Consider user's likely intent
- Provide actionable information
"""
        elif speech_act == SpeechActType.EXPRESSION:
            return f"""
This is an EXPRESSION of feeling/concern. Acknowledge and provide support.

Query: {query}

Requirements:
- Acknowledge user's feeling
- Provide empathetic response
- Offer practical help if relevant
"""
```

#### 4.2 Language Game Context

**Problem:** LLMs miss implicit "language games" (e.g., medical vs. fitness context).

**Solution:** Identify language game and adapt response.

```python
# core/insight/language_games.py
class LanguageGameIdentifier:
    """Identify the "language game" (context/activity) of query."""

    def identify_language_game(self, query: str, context: ConversationContext) -> LanguageGame:
        """Identify which language game user is playing."""
        # Language games: medical, fitness, nutrition, general wellness, etc.

        if self._is_medical_game(query):
            return LanguageGame.MEDICAL  # "Is this a symptom?"
        elif self._is_fitness_game(query):
            return LanguageGame.FITNESS  # "How do I build muscle?"
        elif self._is_nutrition_game(query):
            return LanguageGame.NUTRITION  # "What should I eat?"
        elif self._is_wellness_game(query):
            return LanguageGame.WELLNESS  # "How do I feel better?"
        else:
            return LanguageGame.GENERAL

    def build_game_appropriate_prompt(self, query: str, game: LanguageGame) -> str:
        """Build prompt appropriate for language game."""
        game_rules = {
            LanguageGame.MEDICAL: """
MEDICAL LANGUAGE GAME:
- Do not provide medical diagnosis
- Refer to healthcare professionals
- Provide general wellness information only
""",
            LanguageGame.FITNESS: """
FITNESS LANGUAGE GAME:
- Focus on exercise, training, performance
- Use fitness terminology (sets, reps, progressive overload)
- Consider user's fitness level
""",
            LanguageGame.NUTRITION: """
NUTRITION LANGUAGE GAME:
- Focus on food, nutrients, meal planning
- Use nutrition terminology (macros, micronutrients, RDA)
- Consider dietary constraints
"""
        }

        return f"""
{game_rules.get(game, '')}

Query: {query}

Respond within the appropriate language game context.
"""
```

#### 4.3 Meaning-as-Use Resolution

**Problem:** LLMs rely on dictionary definitions, missing contextual meaning.

**Solution:** Resolve meaning through usage patterns.

```python
# core/insight/meaning_as_use.py
class MeaningAsUseResolver:
    """Resolve meaning through usage patterns (Wittgenstein)."""

    def resolve_meaning(self, term: str, context: ConversationContext) -> str:
        """Resolve term meaning through how it's used in context."""
        # Dictionary definition vs. actual usage
        # e.g., "diet" can mean "restriction" or "eating pattern"

        # Check usage patterns in conversation
        previous_uses = self._find_previous_uses(term, context)
        if previous_uses:
            # Meaning comes from how term was used before
            return self._infer_meaning_from_usage(term, previous_uses)
        else:
            # Fallback to domain-specific meaning
            return self._domain_specific_meaning(term, context.domain)

    def build_usage_aware_prompt(self, query: str, resolved_terms: Dict[str, str]) -> str:
        """Build prompt with resolved term meanings."""
        return f"""
Interpret this query using RESOLVED TERM MEANINGS (from context):

Resolved meanings:
{self._format_resolved_meanings(resolved_terms)}

Query: {query}

Use the resolved meanings, not dictionary definitions.
"""
```

**Example:**
```
Term: "diet"
Previous uses: "I'm on a diet to lose weight" (restriction)
Resolved meaning: "calorie-restricted eating pattern for weight loss"

Query: "What diet should I follow?"
Interpreted as: "What calorie-restricted eating pattern should I follow for weight loss?"
```

---

## 5. Integrated Framework

### Combining All Principles

**Unified Prompt Structure:**

```python
# core/insight/philosophical_prompt_builder.py
class PhilosophicalPromptBuilder:
    """Build prompts applying all philosophical principles."""

    def build_comprehensive_prompt(
        self,
        query: str,
        user_context: UserContext,
        conversation_history: List[Interaction]
    ) -> str:
        """Build prompt applying all philosophical frameworks."""

        # 1. Classify speech act
        speech_act = self.speech_act_classifier.classify_speech_act(query)

        # 2. Identify language game
        language_game = self.language_game_identifier.identify_language_game(query, conversation_history)

        # 3. Resolve ambiguous terms (meaning-as-use)
        resolved_query = self.contextual_resolver.resolve_meaning(query, conversation_history)

        # 4. Build integrated prompt
        return f"""
You are a logical reasoning assistant applying philosophical principles:

1. ARISTOTELIAN LOGIC:
   - Structure answer as syllogism (major premise → minor premise → conclusion)
   - Avoid contradictions (Law of Non-Contradiction)
   - Use categorical logic (distinguish universal/particular)

2. ANALYTICAL PHILOSOPHY:
   - All claims must be VERIFIABLE (cite sources)
   - Claims must be FALSIFIABLE (state falsification condition)
   - Distinguish analytical (definitional) from synthetic (empirical) statements

3. POST-ANALYTICAL PHILOSOPHY:
   - Provide PRACTICALLY USEFUL answers (actionable, testable)
   - Interpret within CONTEXT (hermeneutic circle)
   - Consider user's situation (pragmatic validation)

4. LINGUISTIC PHILOSOPHY:
   - Respond to SPEECH ACT: {speech_act.value}
   - Use LANGUAGE GAME: {language_game.value}
   - Resolve meaning through USAGE, not definitions

User context:
- Age: {user_context.age}
- Goals: {user_context.goals}
- Previous interactions: {self._summarize_history(conversation_history)}

Resolved query (meaning-as-use): {resolved_query.resolved_query}

Original query: {query}

Response format:
MAJOR PREMISE: [General rule, verifiable, falsifiable]
MINOR PREMISE: [Specific case, contextually relevant]
CONCLUSION: [Logical inference, practically useful]

CLAIMS:
- CLAIM 1: [Statement]
  - EVIDENCE: [Source]
  - FALSIFIABLE: Yes/No
  - FALSIFICATION CONDITION: [What would prove it wrong]
  - PRACTICALLY USEFUL: Yes/No
  - ACTIONABLE STEPS: [What user can do]

- CLAIM 2: ...
"""
```

### Validation Pipeline

```python
# core/insight/philosophical_validator.py
class PhilosophicalValidator:
    """Validate LLM responses against all philosophical principles."""

    def validate_comprehensive(
        self,
        response: str,
        original_query: str,
        user_context: UserContext
    ) -> ComprehensiveValidationResult:
        """Validate against all frameworks."""

        results = {}

        # 1. Aristotelian validation
        syllogism_validation = self.syllogistic_validator.validate_syllogism(response)
        contradictions = self.non_contradiction_checker.check_contradictions(response)
        results['aristotelian'] = {
            'syllogism_valid': syllogism_validation.valid,
            'no_contradictions': len(contradictions) == 0,
            'contradictions': contradictions
        }

        # 2. Analytical validation
        verification = self.verification_enforcer.validate_verifiability(response)
        falsifiability = self.falsification_checker.check_falsifiability(response)
        results['analytical'] = {
            'verification_rate': verification.verification_rate,
            'falsifiable': falsifiability.falsifiable,
            'unverified_claims': verification.unverified_claims
        }

        # 3. Post-analytical validation
        pragmatic = self.pragmatic_validator.validate_practical_utility(response, user_context)
        results['post_analytical'] = {
            'practically_useful': pragmatic.practically_useful,
            'actionable': pragmatic.actionable,
            'contextually_relevant': pragmatic.contextually_relevant
        }

        # 4. Linguistic validation
        speech_act_appropriate = self._check_speech_act_appropriateness(response, original_query)
        language_game_appropriate = self._check_language_game_appropriateness(response, user_context)
        results['linguistic'] = {
            'speech_act_appropriate': speech_act_appropriate,
            'language_game_appropriate': language_game_appropriate
        }

        # Overall validation
        all_valid = (
            syllogism_validation.valid and
            len(contradictions) == 0 and
            verification.verification_rate >= 0.7 and
            falsifiability.falsifiable and
            pragmatic.practically_useful
        )

        return ComprehensiveValidationResult(
            valid=all_valid,
            results=results,
            confidence=self._calculate_overall_confidence(results)
        )
```

---

## 6. Implementation Roadmap

### Phase 1: Aristotelian Logic (Week 1-2)
- [ ] Implement `SyllogisticPromptBuilder`
- [ ] Implement `CategoricalValidator`
- [ ] Implement `NonContradictionChecker`
- [ ] Add to validation pipeline
- [ ] Test on sample queries

### Phase 2: Analytical Philosophy (Week 3-4)
- [ ] Implement `VerificationEnforcer`
- [ ] Implement `FalsificationChecker`
- [ ] Implement `AnalyticalSyntheticClassifier`
- [ ] Integrate with fact-checking system
- [ ] Test verification rates

### Phase 3: Post-Analytical Philosophy (Week 5-6)
- [ ] Implement `PragmaticValidator`
- [ ] Implement `HermeneuticInterpreter`
- [ ] Implement `ContextualResolver`
- [ ] Add user context tracking
- [ ] Test contextual relevance

### Phase 4: Linguistic Philosophy (Week 7-8)
- [ ] Implement `SpeechActClassifier`
- [ ] Implement `LanguageGameIdentifier`
- [ ] Implement `MeaningAsUseResolver`
- [ ] Integrate with conversation history
- [ ] Test speech act classification accuracy

### Phase 5: Integration (Week 9-10)
- [ ] Implement `PhilosophicalPromptBuilder` (unified)
- [ ] Implement `PhilosophicalValidator` (comprehensive)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation

---

## 7. Expected Impact

### Reliability Metrics

**Before (baseline):**
- Contradiction rate: ~15% (estimated)
- Unverifiable claims: ~30%
- Contextually irrelevant: ~25%
- Unfalsifiable claims: ~20%

**After (target):**
- Contradiction rate: <2%
- Unverifiable claims: <5%
- Contextually irrelevant: <10%
- Unfalsifiable claims: <5%

### User Experience

- **Clarity:** Structured syllogistic responses easier to understand
- **Trust:** Verifiable claims with sources increase trust
- **Usefulness:** Pragmatic validation ensures actionable answers
- **Relevance:** Contextual resolution improves personalization

---

## 8. References

### Philosophical Sources

1. **Aristotelian Logic:**
   - Aristotle, "Organon" (Categories, Prior Analytics)
   - Smith, R. (2018). "Aristotle's Logic" (Stanford Encyclopedia)

2. **Analytical Philosophy:**
   - Ayer, A.J. (1936). "Language, Truth and Logic"
   - Popper, K. (1959). "The Logic of Scientific Discovery"
   - Carnap, R. (1950). "Logical Foundations of Probability"

3. **Post-Analytical Philosophy:**
   - Rorty, R. (1979). "Philosophy and the Mirror of Nature"
   - Gadamer, H.G. (1960). "Truth and Method"
   - Dewey, J. (1929). "The Quest for Certainty"

4. **Linguistic Philosophy:**
   - Wittgenstein, L. (1953). "Philosophical Investigations"
   - Austin, J.L. (1962). "How to Do Things with Words"
   - Searle, J. (1969). "Speech Acts"

### AI/LLM Applications

- Bender, E.M. & Koller, A. (2020). "Climbing towards NLU: On Meaning, Form, and Understanding in the Age of Data"
- Mitchell, M. (2023). "Why AI is Harder Than We Think"
- Bisk, Y. et al. (2020). "Experience Grounds Language"

---

## 9. Integration with Existing Systems

### Connection to Current Implementation

**Existing systems to integrate with:**
- `core/insight/fact_checker.py` (verification principle)
- `core/insight/confidence.py` (falsification principle)
- `core/insight/guardrails.py` (speech act filtering)
- `core/rag/simple_rag.py` (contextual resolution)

**New modules to create:**
- `core/insight/aristotelian/` (syllogistic logic)
- `core/insight/analytical/` (verification, falsification)
- `core/insight/post_analytical/` (pragmatic, hermeneutic)
- `core/insight/linguistic/` (speech acts, language games)

---

**Last Updated:** 2026-01-28
**Status:** Design Document — Ready for Implementation Planning
