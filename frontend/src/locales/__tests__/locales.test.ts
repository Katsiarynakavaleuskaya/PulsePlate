/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import en from "../en.json";
import es from "../es.json";
import ru from "../ru.json";

/**
 * Comprehensive locale validation tests
 * These tests ensure translation files maintain structural integrity,
 * completeness, and consistency across all supported languages.
 */
describe("Locale Files Validation", () => {
  describe("JSON Structure and Syntax", () => {
    it("should parse English locale without errors", () => {
      expect(en).toBeDefined();
      expect(typeof en).toBe("object");
    });

    it("should parse Spanish locale without errors", () => {
      expect(es).toBeDefined();
      expect(typeof es).toBe("object");
    });

    it("should parse Russian locale without errors", () => {
      expect(ru).toBeDefined();
      expect(typeof ru).toBe("object");
    });
  });

  describe("Key Completeness", () => {
    /**
     * Recursively extracts all keys from a nested object
     * @param obj - The object to extract keys from
     * @param prefix - Current path prefix for nested keys
     * @returns Set of all dot-notation keys
     */
    function getAllKeys(obj: Record<string, unknown>, prefix = ""): Set<string> {
      const keys = new Set<string>();

      for (const [key, value] of Object.entries(obj)) {
        const fullKey = prefix ? `${prefix}.${key}` : key;

        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
          const nestedKeys = getAllKeys(value as Record<string, unknown>, fullKey);
          nestedKeys.forEach((k) => keys.add(k));
        } else {
          keys.add(fullKey);
        }
      }

      return keys;
    }

    it("should have all English keys in Spanish locale", () => {
      const enKeys = getAllKeys(en);
      const esKeys = getAllKeys(es);

      const missingKeys = Array.from(enKeys).filter((key) => !esKeys.has(key));

      expect(missingKeys).toEqual([]);
      expect(esKeys.size).toBe(enKeys.size);
    });

    it("should have all English keys in Russian locale", () => {
      const enKeys = getAllKeys(en);
      const ruKeys = getAllKeys(ru);

      const missingKeys = Array.from(enKeys).filter((key) => !ruKeys.has(key));

      expect(missingKeys).toEqual([]);
      expect(ruKeys.size).toBe(enKeys.size);
    });

    it("should not have extra keys in Spanish locale", () => {
      const enKeys = getAllKeys(en);
      const esKeys = getAllKeys(es);

      const extraKeys = Array.from(esKeys).filter((key) => !enKeys.has(key));

      expect(extraKeys).toEqual([]);
    });

    it("should not have extra keys in Russian locale", () => {
      const enKeys = getAllKeys(en);
      const ruKeys = getAllKeys(ru);

      const extraKeys = Array.from(ruKeys).filter((key) => !enKeys.has(key));

      expect(extraKeys).toEqual([]);
    });
  });

  describe("Translation Value Validation", () => {
    /**
     * Recursively validates that no translation values are empty
     * @param obj - The object to validate
     * @param path - Current path for error reporting
     * @returns Array of paths with empty values
     */
    function findEmptyValues(
      obj: Record<string, unknown>,
      path = ""
    ): string[] {
      const emptyPaths: string[] = [];

      for (const [key, value] of Object.entries(obj)) {
        const currentPath = path ? `${path}.${key}` : key;

        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
          emptyPaths.push(
            ...findEmptyValues(value as Record<string, unknown>, currentPath)
          );
        } else if (typeof value === "string") {
          if (value.trim().length === 0) {
            emptyPaths.push(currentPath);
          }
        }
      }

      return emptyPaths;
    }

    it("should not have empty translation strings in English", () => {
      const emptyPaths = findEmptyValues(en);
      expect(emptyPaths).toEqual([]);
    });

    it("should not have empty translation strings in Spanish", () => {
      const emptyPaths = findEmptyValues(es);
      expect(emptyPaths).toEqual([]);
    });

    it("should not have empty translation strings in Russian", () => {
      const emptyPaths = findEmptyValues(ru);
      expect(emptyPaths).toEqual([]);
    });
  });

  describe("Structural Consistency", () => {
    /**
     * Gets the structure of an object (types at each level)
     * @param obj - The object to analyze
     * @param path - Current path
     * @returns Map of paths to their types
     */
    function getStructure(
      obj: Record<string, unknown>,
      path = ""
    ): Map<string, string> {
      const structure = new Map<string, string>();

      for (const [key, value] of Object.entries(obj)) {
        const currentPath = path ? `${path}.${key}` : key;

        if (value === null) {
          structure.set(currentPath, "null");
        } else if (Array.isArray(value)) {
          structure.set(currentPath, "array");
        } else if (typeof value === "object") {
          structure.set(currentPath, "object");
          const nested = getStructure(value as Record<string, unknown>, currentPath);
          nested.forEach((type, nestedPath) => structure.set(nestedPath, type));
        } else {
          structure.set(currentPath, typeof value);
        }
      }

      return structure;
    }

    it("should have matching structure between English and Spanish", () => {
      const enStructure = getStructure(en);
      const esStructure = getStructure(es);

      // Check all English paths exist in Spanish with same type
      for (const [path, type] of enStructure) {
        expect(esStructure.has(path)).toBe(true);
        expect(esStructure.get(path)).toBe(type);
      }
    });

    it("should have matching structure between English and Russian", () => {
      const enStructure = getStructure(en);
      const ruStructure = getStructure(ru);

      // Check all English paths exist in Russian with same type
      for (const [path, type] of enStructure) {
        expect(ruStructure.has(path)).toBe(true);
        expect(ruStructure.get(path)).toBe(type);
      }
    });
  });

  describe("Top-Level Sections", () => {
    const expectedSections = ["common", "shoplist", "paywall"];

    it("should have all required sections in English", () => {
      const sections = Object.keys(en);
      expect(sections.sort()).toEqual(expectedSections.sort());
    });

    it("should have all required sections in Spanish", () => {
      const sections = Object.keys(es);
      expect(sections.sort()).toEqual(expectedSections.sort());
    });

    it("should have all required sections in Russian", () => {
      const sections = Object.keys(ru);
      expect(sections.sort()).toEqual(expectedSections.sort());
    });
  });

  describe("Common Section", () => {
    const expectedKeys = ["ok", "cancel"];

    it("should have correct common keys in all locales", () => {
      expect(Object.keys(en.common).sort()).toEqual(expectedKeys.sort());
      expect(Object.keys(es.common).sort()).toEqual(expectedKeys.sort());
      expect(Object.keys(ru.common).sort()).toEqual(expectedKeys.sort());
    });

    it("should have non-empty common translations", () => {
      expect(en.common.ok).toBeTruthy();
      expect(en.common.cancel).toBeTruthy();
      expect(es.common.ok).toBeTruthy();
      expect(es.common.cancel).toBeTruthy();
      expect(ru.common.ok).toBeTruthy();
      expect(ru.common.cancel).toBeTruthy();
    });
  });

  describe("Shopping List Section", () => {
    const expectedKeys = ["loading", "error", "empty"];

    it("should have correct shoplist keys in all locales", () => {
      expect(Object.keys(en.shoplist).sort()).toEqual(expectedKeys.sort());
      expect(Object.keys(es.shoplist).sort()).toEqual(expectedKeys.sort());
      expect(Object.keys(ru.shoplist).sort()).toEqual(expectedKeys.sort());
    });

    it("should have non-empty shoplist translations", () => {
      expect(en.shoplist.loading).toBeTruthy();
      expect(en.shoplist.error).toBeTruthy();
      expect(en.shoplist.empty).toBeTruthy();
      expect(es.shoplist.loading).toBeTruthy();
      expect(es.shoplist.error).toBeTruthy();
      expect(es.shoplist.empty).toBeTruthy();
      expect(ru.shoplist.loading).toBeTruthy();
      expect(ru.shoplist.error).toBeTruthy();
      expect(ru.shoplist.empty).toBeTruthy();
    });
  });

  describe("Paywall Section", () => {
    const topLevelKeys = ["title", "subtitle", "cta", "legal", "before", "after", "items"];
    const beforeAfterKeys = ["label", "randomPlate", "macrosOnly", "manualShopping"];
    const afterExtraKeys = ["personalPlate", "microBalance", "autoShoppingList"];
    const itemsBeforeKeys = ["random_plate", "macros_only", "manual_shopping"];
    const itemsAfterKeys = ["personal_plate", "micro_balance", "auto_shopping_list"];

    it("should have correct paywall top-level keys in all locales", () => {
      expect(Object.keys(en.paywall).sort()).toEqual(topLevelKeys.sort());
      expect(Object.keys(es.paywall).sort()).toEqual(topLevelKeys.sort());
      expect(Object.keys(ru.paywall).sort()).toEqual(topLevelKeys.sort());
    });

    it("should have correct before subsection keys in all locales", () => {
      expect(Object.keys(en.paywall.before).sort()).toEqual(beforeAfterKeys.sort());
      expect(Object.keys(es.paywall.before).sort()).toEqual(beforeAfterKeys.sort());
      expect(Object.keys(ru.paywall.before).sort()).toEqual(beforeAfterKeys.sort());
    });

    it("should have correct after subsection keys in all locales", () => {
      const afterKeys = [...beforeAfterKeys.slice(0, 1), ...afterExtraKeys];
      expect(Object.keys(en.paywall.after).sort()).toEqual(afterKeys.sort());
      expect(Object.keys(es.paywall.after).sort()).toEqual(afterKeys.sort());
      expect(Object.keys(ru.paywall.after).sort()).toEqual(afterKeys.sort());
    });

    it("should have correct items.before keys in all locales", () => {
      expect(Object.keys(en.paywall.items.before).sort()).toEqual(itemsBeforeKeys.sort());
      expect(Object.keys(es.paywall.items.before).sort()).toEqual(itemsBeforeKeys.sort());
      expect(Object.keys(ru.paywall.items.before).sort()).toEqual(itemsBeforeKeys.sort());
    });

    it("should have correct items.after keys in all locales", () => {
      expect(Object.keys(en.paywall.items.after).sort()).toEqual(itemsAfterKeys.sort());
      expect(Object.keys(es.paywall.items.after).sort()).toEqual(itemsAfterKeys.sort());
      expect(Object.keys(ru.paywall.items.after).sort()).toEqual(itemsAfterKeys.sort());
    });

    it("should have non-empty paywall translations in Spanish", () => {
      expect(es.paywall.title).toBeTruthy();
      expect(es.paywall.subtitle).toBeTruthy();
      expect(es.paywall.cta).toBeTruthy();
      expect(es.paywall.legal).toBeTruthy();
      expect(es.paywall.before.label).toBeTruthy();
      expect(es.paywall.after.label).toBeTruthy();
    });

    it("should have non-empty paywall translations in Russian", () => {
      expect(ru.paywall.title).toBeTruthy();
      expect(ru.paywall.subtitle).toBeTruthy();
      expect(ru.paywall.cta).toBeTruthy();
      expect(ru.paywall.legal).toBeTruthy();
      expect(ru.paywall.before.label).toBeTruthy();
      expect(ru.paywall.after.label).toBeTruthy();
    });
  });

  describe("Spanish Translation Quality (Branch Changes)", () => {
    it("should have updated empty state translation", () => {
      expect(es.shoplist.empty).toBe("Lista vacía.");
      expect(es.shoplist.empty).not.toBe("Vacío.");
    });

    it("should have improved paywall subtitle", () => {
      expect(es.paywall.subtitle).toBe("Plan nutricional personal, equilibrio preciso, planificación semanal.");
      expect(es.paywall.subtitle).not.toContain("Plato personal");
      expect(es.paywall.subtitle).not.toContain("microequilibrio");
    });

    it("should use 'Configuración' instead of 'Ajustes' in legal text", () => {
      expect(es.paywall.legal).toContain("Configuración");
      expect(es.paywall.legal).not.toContain("Ajustes");
    });

    it("should use full term 'macronutrientes' instead of 'macros'", () => {
      expect(es.paywall.before.macrosOnly).toBe("Solo macronutrientes");
      expect(es.paywall.items.before.macros_only).toBe("Solo macronutrientes");
    });

    it("should use 'Plan nutricional personal' instead of 'Plato personal'", () => {
      expect(es.paywall.after.personalPlate).toBe("Plan nutricional personal");
      expect(es.paywall.items.after.personal_plate).toBe("Plan nutricional personal");
    });

    it("should use 'Equilibrio nutricional' instead of 'Microequilibrio'", () => {
      expect(es.paywall.after.microBalance).toBe("Equilibrio nutricional");
      expect(es.paywall.items.after.micro_balance).toBe("Equilibrio nutricional");
    });
  });

  describe("Russian Translation Quality (Branch Changes)", () => {
    it("should have improved paywall subtitle", () => {
      expect(ru.paywall.subtitle).toBe("Персональный рацион, точный баланс, недельная программа.");
      expect(ru.paywall.subtitle).not.toContain("Персональная тарелка");
      expect(ru.paywall.subtitle).not.toContain("микро-баланс");
    });

    it("should use 'рацион' instead of 'тарелка'", () => {
      expect(ru.paywall.before.randomPlate).toBe("Случайный рацион");
      expect(ru.paywall.after.personalPlate).toBe("Персональный рацион");
      expect(ru.paywall.items.before.random_plate).toBe("Случайный рацион");
      expect(ru.paywall.items.after.personal_plate).toBe("Персональный рацион");
    });

    it("should use full term 'макронутриенты' instead of 'макро'", () => {
      expect(ru.paywall.before.macrosOnly).toBe("Только макронутриенты");
      expect(ru.paywall.items.before.macros_only).toBe("Только макронутриенты");
    });

    it("should use 'Точный баланс' instead of 'Микро-баланс'", () => {
      expect(ru.paywall.after.microBalance).toBe("Точный баланс");
      expect(ru.paywall.items.after.micro_balance).toBe("Точный баланс");
    });

    it("should use 'Автосписок покупок' (one word) instead of 'Авто список покупок'", () => {
      expect(ru.paywall.after.autoShoppingList).toBe("Автосписок покупок");
      expect(ru.paywall.items.after.auto_shopping_list).toBe("Автосписок покупок");
    });
  });

  describe("Character Encoding and Special Characters", () => {
    it("should handle Spanish special characters correctly", () => {
      // Spanish uses: á, é, í, ó, ú, ñ, ¿, ¡
      const spanishText = JSON.stringify(es);
      expect(spanishText).toContain("Cargando");
      expect(spanishText).toContain("Configuración");
      expect(spanishText).toContain("Suscripción");
    });

    it("should handle Russian Cyrillic characters correctly", () => {
      const russianText = JSON.stringify(ru);
      expect(russianText).toMatch(/[\u0400-\u04FF]/); // Cyrillic range
      expect(ru.common.ok).toBe("ОК");
      expect(ru.common.cancel).toBe("Отмена");
    });

    it("should not have any mojibake or encoding issues", () => {
      // Check for common mojibake patterns
      const spanishText = JSON.stringify(es);
      const russianText = JSON.stringify(ru);

      expect(spanishText).not.toMatch(/Ã|Â|Ñ/); // Common UTF-8 mojibake
      expect(russianText).not.toMatch(/Ð|Ñ[^ñ]/); // Cyrillic mojibake
    });
  });

  describe("Translation Length Validation", () => {
    /**
     * Checks if translations are reasonable length (not too short or absurdly long)
     */
    function validateTranslationLength(
      obj: Record<string, unknown>,
      path = ""
    ): { path: string; length: number }[] {
      const issues: { path: string; length: number }[] = [];

      for (const [key, value] of Object.entries(obj)) {
        const currentPath = path ? `${path}.${key}` : key;

        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
          issues.push(
            ...validateTranslationLength(value as Record<string, unknown>, currentPath)
          );
        } else if (typeof value === "string") {
          // Flag if too short (< 2 chars) or too long (> 200 chars)
          if (value.length < 2 || value.length > 200) {
            issues.push({ path: currentPath, length: value.length });
          }
        }
      }

      return issues;
    }

    it("should have reasonable translation lengths in Spanish", () => {
      const issues = validateTranslationLength(es);
      expect(issues).toEqual([]);
    });

    it("should have reasonable translation lengths in Russian", () => {
      const issues = validateTranslationLength(ru);
      expect(issues).toEqual([]);
    });
  });

  describe("Consistency Between Duplicate Keys", () => {
    it("should have consistent Spanish translations for before/items.before", () => {
      expect(es.paywall.before.randomPlate).toBe(es.paywall.items.before.random_plate);
      expect(es.paywall.before.macrosOnly).toBe(es.paywall.items.before.macros_only);
      expect(es.paywall.before.manualShopping).toBe(es.paywall.items.before.manual_shopping);
    });

    it("should have consistent Spanish translations for after/items.after", () => {
      expect(es.paywall.after.personalPlate).toBe(es.paywall.items.after.personal_plate);
      expect(es.paywall.after.microBalance).toBe(es.paywall.items.after.micro_balance);
      expect(es.paywall.after.autoShoppingList).toBe(es.paywall.items.after.auto_shopping_list);
    });

    it("should have consistent Russian translations for before/items.before", () => {
      expect(ru.paywall.before.randomPlate).toBe(ru.paywall.items.before.random_plate);
      expect(ru.paywall.before.macrosOnly).toBe(ru.paywall.items.before.macros_only);
      expect(ru.paywall.before.manualShopping).toBe(ru.paywall.items.before.manual_shopping);
    });

    it("should have consistent Russian translations for after/items.after", () => {
      expect(ru.paywall.after.personalPlate).toBe(ru.paywall.items.after.personal_plate);
      expect(ru.paywall.after.microBalance).toBe(ru.paywall.items.after.micro_balance);
      expect(ru.paywall.after.autoShoppingList).toBe(ru.paywall.items.after.auto_shopping_list);
    });
  });

  describe("Punctuation and Formatting", () => {
    it("should have proper punctuation in Spanish translations", () => {
      // Spanish uses dots for complete sentences
      expect(es.shoplist.empty).toMatch(/\.$/);
      expect(es.paywall.subtitle).toMatch(/\.$/);
      expect(es.paywall.legal).toMatch(/\.$/);
    });

    it("should have proper punctuation in Russian translations", () => {
      // Russian uses dots for complete sentences
      expect(ru.shoplist.empty).toMatch(/\.$/);
      expect(ru.paywall.subtitle).toMatch(/\.$/);
      expect(ru.paywall.legal).toMatch(/\.$/);
    });

    it("should have consistent ellipsis usage in loading messages", () => {
      expect(en.shoplist.loading).toContain("…");
      expect(es.shoplist.loading).toContain("…");
      expect(ru.shoplist.loading).toContain("…");
    });
  });

  describe("No Placeholder or Debug Text", () => {
    /**
     * Checks for common placeholder patterns that shouldn't be in production
     */
    function findPlaceholders(
      obj: Record<string, unknown>,
      path = ""
    ): string[] {
      const placeholders: string[] = [];
      const placeholderPatterns = [
        /TODO/i,
        /FIXME/i,
        /XXX/i,
        /\[.*\]/,
        /{.*}/,
        /Lorem ipsum/i,
        /test/i,
        /placeholder/i,
      ];

      for (const [key, value] of Object.entries(obj)) {
        const currentPath = path ? `${path}.${key}` : key;

        if (value !== null && typeof value === "object" && !Array.isArray(value)) {
          placeholders.push(
            ...findPlaceholders(value as Record<string, unknown>, currentPath)
          );
        } else if (typeof value === "string") {
          for (const pattern of placeholderPatterns) {
            if (pattern.test(value)) {
              placeholders.push(`${currentPath}: ${value}`);
              break;
            }
          }
        }
      }

      return placeholders;
    }

    it("should not have placeholder text in Spanish", () => {
      const placeholders = findPlaceholders(es);
      expect(placeholders).toEqual([]);
    });

    it("should not have placeholder text in Russian", () => {
      const placeholders = findPlaceholders(ru);
      expect(placeholders).toEqual([]);
    });
  });
});