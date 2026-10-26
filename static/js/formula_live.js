
document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const manualInputs = Array.from(
        document.querySelectorAll(".result-input")
    );

    const formulaInputs = Array.from(
        document.querySelectorAll(".formula-result")
    );

    // --------------------------------------------------
    // NORMALIZE PARAMETER NAMES
    // --------------------------------------------------
    function normalizeName(name) {
        let value = String(name || "")
            .trim()
            .toUpperCase();

        // R.B.C Count -> RBC Count
        // R.B.C_COUNT -> RBC_COUNT
        value = value.replace(/\./g, "");

        // Convert remaining punctuation and spaces to underscores.
        value = value.replace(/[^A-Z0-9]+/g, "_");

        return value.replace(/^_+|_+$/g, "");
    }

    // --------------------------------------------------
    // COLLECT ALIASES FOR EACH INPUT
    // --------------------------------------------------
    function getAliases(input) {
        const aliases = [
            input.dataset.code,
            input.dataset.shortName,
            input.dataset.displayName,
            input.id,
            input.name
        ];

        const displayName = String(
            input.dataset.displayName || ""
        );

        // Hemoglobin (Hb) -> also register HB.
        const parentheticalMatches =
            displayName.matchAll(/\(([^)]+)\)/g);

        for (const match of parentheticalMatches) {
            aliases.push(match[1]);
        }

        // Add the numeric parameter ID as an alias.
        const fieldName = String(input.name || "");
        const idMatch = fieldName.match(/^param_(\d+)$/i);

        if (idMatch) {
            aliases.push("PARAM_" + idMatch[1]);
        }

        const normalized = aliases
            .map(normalizeName)
            .filter(Boolean);

        // Add known CBC aliases.
        const expanded = [];

        normalized.forEach(function (alias) {
            expanded.push(alias);

            // RBC aliases
            if (
                alias === "RBC" ||
                alias === "R_B_C" ||
                alias === "RBC_COUNT" ||
                alias === "R_B_C_COUNT"
            ) {
                expanded.push("RBC");
                expanded.push("RBC_COUNT");
                expanded.push("R_B_C_COUNT");
            }

            // Hemoglobin aliases
            if (
                alias === "HB" ||
                alias === "HEMOGLOBIN" ||
                alias === "HEMOGLOBIN_HB"
            ) {
                expanded.push("HB");
                expanded.push("HEMOGLOBIN");
                expanded.push("HEMOGLOBIN_HB");
            }

            // Hematocrit / packed cell volume aliases
            if (
                alias === "HCT" ||
                alias === "PCV" ||
                alias === "PACKED_CELL_VOLUME_HCT"
            ) {
                expanded.push("HCT");
                expanded.push("PCV");
                expanded.push("PACKED_CELL_VOLUME_HCT");
            }
        });

        return [...new Set(expanded)];
    }

    // --------------------------------------------------
    // READ CURRENT VALUES
    // --------------------------------------------------
    function readValues() {
        const values = {};

        function addInput(input) {
            const rawValue = String(input.value || "").trim();

            if (rawValue === "") {
                return;
            }

            const value = Number(rawValue);

            if (!Number.isFinite(value)) {
                return;
            }

            getAliases(input).forEach(function (alias) {
                values[alias] = value;
            });
        }

        manualInputs.forEach(addInput);
        formulaInputs.forEach(addInput);

        return values;
    }

    // --------------------------------------------------
    // SAFE ARITHMETIC EXPRESSION EVALUATOR
    // Supports + - * / % and parentheses.
    // --------------------------------------------------
    function calculateExpression(expression) {
        const source = String(expression || "")
            .replace(/×/g, "*")
            .replace(/÷/g, "/")
            .replace(/\s+/g, "");

        if (!source) {
            return null;
        }

        const tokens = source.match(
            /(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|[()+\-*/%]/gi
        );

        if (!tokens || tokens.join("") !== source) {
            return null;
        }

        let position = 0;

        function parsePrimary() {
            const token = tokens[position++];

            if (token === "(") {
                const value = parseExpression();

                if (tokens[position++] !== ")") {
                    throw new Error("Missing closing parenthesis");
                }

                return value;
            }

            if (token === "+") {
                return parsePrimary();
            }

            if (token === "-") {
                return -parsePrimary();
            }

            if (token === undefined || !/^(\d|\.)/.test(token)) {
                throw new Error("Expected a number");
            }

            const number = Number(token);

            if (!Number.isFinite(number)) {
                throw new Error("Invalid number");
            }

            return number;
        }

        function parseTerm() {
            let value = parsePrimary();

            while (
                tokens[position] === "*" ||
                tokens[position] === "/" ||
                tokens[position] === "%"
            ) {
                const operator = tokens[position++];
                const right = parsePrimary();

                if (
                    (operator === "/" || operator === "%") &&
                    right === 0
                ) {
                    throw new Error("Division by zero");
                }

                if (operator === "*") {
                    value *= right;
                } else if (operator === "/") {
                    value /= right;
                } else {
                    value %= right;
                }
            }

            return value;
        }

        function parseExpression() {
            let value = parseTerm();

            while (
                tokens[position] === "+" ||
                tokens[position] === "-"
            ) {
                const operator = tokens[position++];
                const right = parseTerm();

                value = operator === "+"
                    ? value + right
                    : value - right;
            }

            return value;
        }

        try {
            const result = parseExpression();

            if (position !== tokens.length) {
                return null;
            }

            return Number.isFinite(result) ? result : null;
        } catch (error) {
            return null;
        }
    }

    // --------------------------------------------------
    // SUBSTITUTE FORMULA VARIABLES
    // --------------------------------------------------
    function calculateFormula(expression, values) {
        if (!expression) {
            return null;
        }

        let processed = String(expression)
            .toUpperCase()
            .replace(/×/g, "*")
            .replace(/÷/g, "/");

        // Replace longer variable names first.
        const keys = Object.keys(values).sort(
            function (a, b) {
                return b.length - a.length;
            }
        );

        keys.forEach(function (key) {
            const escaped = key.replace(
                /[.*+?^${}()|[\]\\]/g,
                "\\$&"
            );

            const pattern = new RegExp(
                "(?<![A-Z0-9_])" +
                escaped +
                "(?![A-Z0-9_])",
                "g"
            );

            processed = processed.replace(
                pattern,
                String(values[key])
            );
        });

        // Do not calculate if variables remain unresolved.
        if (/[A-Z_][A-Z0-9_]*/i.test(processed)) {
            return null;
        }

        return calculateExpression(processed);
    }

    // --------------------------------------------------
    // RECALCULATE FORMULA FIELDS
    // --------------------------------------------------
    function updateFormulaFields() {
        const values = readValues();

        let pending = formulaInputs.slice();
        let pass = 0;

        while (
            pending.length > 0 &&
            pass < formulaInputs.length + 1
        ) {
            pass++;

            let calculatedSomething = false;
            const remaining = [];

            pending.forEach(function (input) {
                const formula = input.dataset.formula;

                if (!formula) {
                    remaining.push(input);
                    return;
                }

                const result = calculateFormula(formula, values);

                if (result === null) {
                    remaining.push(input);
                    return;
                }

                const parsedDecimals = parseInt(
                    input.dataset.decimals || "2",
                    10
                );

                const decimals = Number.isFinite(parsedDecimals)
                    ? Math.max(0, Math.min(10, parsedDecimals))
                    : 2;

                input.value = result.toFixed(decimals);

                // Make this result available to dependent formulas.
                getAliases(input).forEach(function (alias) {
                    values[alias] = result;
                });

                calculatedSomething = true;
            });

            pending = remaining;

            if (!calculatedSomething) {
                break;
            }
        }

        // Keep unresolved formulas empty.
        pending.forEach(function (input) {
            input.value = "";
        });
    }

    // --------------------------------------------------
    // LISTEN FOR USER INPUT
    // --------------------------------------------------
    manualInputs.forEach(function (input) {
        input.addEventListener("input", updateFormulaFields);
        input.addEventListener("change", updateFormulaFields);
    });

    // Recalculate on page load.
    updateFormulaFields();

    // --------------------------------------------------
    // DIAGNOSTICS
    // --------------------------------------------------
    console.info("[Formula Live] Initialized", {
        manualFields: manualInputs.length,
        formulaFields: formulaInputs.length,

        formulaExpressions: formulaInputs.map(function (input) {
            return {
                id: input.id,
                name: input.name,
                formula: input.dataset.formula,
                code: input.dataset.code,
                shortName: input.dataset.shortName,
                displayName: input.dataset.displayName
            };
        })
    });
});

