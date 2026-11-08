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

        value = value.replace(/\./g, "");
        value = value.replace(/[^A-Z0-9]+/g, "_");

        return value.replace(/^_+|_+$/g, "");
    }

    // --------------------------------------------------
    // DIFFERENTIAL WBC ALIASES
    // --------------------------------------------------
    function expandAliases(alias) {
        const synonymMap = {
            "NEUTROPHIL": ["NEUTROPHIL", "NEUTROPHILS"],
            "NEUTROPHILS": ["NEUTROPHIL", "NEUTROPHILS"],

            "LYMPHOCYTE": ["LYMPHOCYTE", "LYMPHOCYTES"],
            "LYMPHOCYTES": ["LYMPHOCYTE", "LYMPHOCYTES"],

            "MONOCYTE": ["MONOCYTE", "MONOCYTES"],
            "MONOCYTES": ["MONOCYTE", "MONOCYTES"],

            "EOSINOPHIL": ["EOSINOPHIL", "EOSINOPHILS"],
            "EOSINOPHILS": ["EOSINOPHIL", "EOSINOPHILS"],

            "BASOPHIL": ["BASOPHIL", "BASOPHILS"],
            "BASOPHILS": ["BASOPHIL", "BASOPHILS"]
        };

        return synonymMap[alias] || [alias];
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

        const parentheticalMatches =
            displayName.matchAll(/\(([^)]+)\)/g);

        for (const match of parentheticalMatches) {
            aliases.push(match[1]);
        }

        const fieldName = String(input.name || "");
        const idMatch = fieldName.match(/^param_(\d+)$/i);

        if (idMatch) {
            aliases.push("PARAM_" + idMatch[1]);
        }

        const normalized = aliases
            .map(normalizeName)
            .filter(Boolean);

        const expanded = [];

        normalized.forEach(function (alias) {
            expanded.push(...expandAliases(alias));

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

            // Hematocrit aliases
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
    // Supports + - * / % and parentheses
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

        const normalizedValues = {};

        Object.keys(values || {}).forEach(function (key) {
            const normalizedKey = normalizeName(key);

            if (normalizedKey) {
                normalizedValues[normalizedKey] = values[key];
            }
        });

        // Resolve bracketed formula variables.
        let missingVariable = false;

        processed = processed.replace(
            /\[([^\]]+)\]/g,
            function (match, variableName) {
                const normalizedVariable =
                    normalizeName(variableName);

                if (
                    !normalizedVariable ||
                    !Object.prototype.hasOwnProperty.call(
                        normalizedValues,
                        normalizedVariable
                    )
                ) {
                    console.warn(
                        "[Formula Live] Missing formula variable:",
                        variableName
                    );

                    missingVariable = true;
                    return match;
                }

                const numericValue = Number(
                    normalizedValues[normalizedVariable]
                );

                if (!Number.isFinite(numericValue)) {
                    missingVariable = true;
                    return match;
                }

                return String(numericValue);
            }
        );

        if (
            missingVariable ||
            processed.includes("[") ||
            processed.includes("]")
        ) {
            return null;
        }

        // Support unbracketed normalized aliases.
        const keys = Object.keys(normalizedValues).sort(
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
                String(normalizedValues[key])
            );
        });

        if (/[A-Z_][A-Z0-9_]*/i.test(processed)) {
            return null;
        }

        return calculateExpression(processed);
    }

    // --------------------------------------------------
    // RECALCULATE FORMULA FIELDS
    // --------------------------------------------------
    function updateFormulaFields() {
        // Clear old calculated values.
        formulaInputs.forEach(function (input) {
            input.value = "";
        });

        // Start with manually entered values.
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

                const result = calculateFormula(
                    formula,
                    values
                );

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

                // Make calculated results available to dependent formulas.
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

        // Unresolved formulas remain empty.
        pending.forEach(function (input) {
            input.value = "";
        });
    }

    // --------------------------------------------------
    // LISTEN FOR USER INPUT
    // --------------------------------------------------
    manualInputs.forEach(function (input) {
        input.addEventListener(
            "input",
            updateFormulaFields
        );

        input.addEventListener(
            "change",
            updateFormulaFields
        );
    });

    // Recalculate when the page loads.
    updateFormulaFields();

    // --------------------------------------------------
    // DIAGNOSTICS
    // --------------------------------------------------
    console.info("[Formula Live] Initialized", {
        manualFields: manualInputs.length,
        formulaFields: formulaInputs.length,

        formulaExpressions: formulaInputs.map(
            function (input) {
                return {
                    id: input.id,
                    name: input.name,
                    formula: input.dataset.formula,
                    code: input.dataset.code,
                    shortName: input.dataset.shortName,
                    displayName: input.dataset.displayName
                };
            }
        )
    });
});
document.addEventListener("DOMContentLoaded", function () {

    const differentialCodes = [
        "NEUTROPHIL",
        "LYMPHOCYTES",
        "EOSINOPHIL",
        "MONOCYTES",
        "BASOPHILS"
    ];

    const differentialInputs = Array.from(
        document.querySelectorAll(".result-input")
    ).filter(input =>
        differentialCodes.includes(
            (input.dataset.code || "").trim().toUpperCase()
        )
    );

    if (differentialInputs.length !== 5) {
        console.warn(
            "Differential WBC validation: Expected 5 inputs, found",
            differentialInputs.length
        );
    }

    function getValue(input) {
        const value = parseFloat(input.value);
        return Number.isFinite(value) ? value : 0;
    }

    function calculateTotal() {
        return differentialInputs.reduce(
            (total, input) => total + getValue(input),
            0
        );
    }

    // Prevent the total from exceeding 100%
    differentialInputs.forEach(input => {

        input.addEventListener("input", function () {

            const otherTotal = differentialInputs
                .filter(other => other !== input)
                .reduce((total, other) => total + getValue(other), 0);

            const maximumAllowed = Math.max(0, 100 - otherTotal);

            const currentValue = parseFloat(input.value);

            if (
                Number.isFinite(currentValue) &&
                currentValue > maximumAllowed
            ) {
                input.value = maximumAllowed;

                input.dispatchEvent(
                    new Event("change", { bubbles: true })
                );
            }

        });

    });

    // Validate exact 100% when saving
    const resultForm = document.querySelector("form[method='POST']");

    if (resultForm) {

        resultForm.addEventListener("submit", function (event) {

            const total = calculateTotal();

            if (Math.abs(total - 100) > 0.001) {

                event.preventDefault();

                alert(
                    "Differential WBC percentages must total exactly 100%.\n" +
                    "Current Total: " + total.toFixed(2) + "%\n\n" +
                    "Please correct Neutrophil, Lymphocytes, Eosinophils, " +
                    "Monocytes and Basophils."
                );

                differentialInputs.forEach(input => {
                    input.classList.add("is-invalid");
                });

                return false;
            }

            differentialInputs.forEach(input => {
                input.classList.remove("is-invalid");
            });

        });

    }

});