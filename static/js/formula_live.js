document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    const manualInputs = Array.from(
        document.querySelectorAll(".result-input")
    );

    const formulaInputs = Array.from(
        document.querySelectorAll(".formula-result")
    );

    // Normalize parameter names and codes.
    function normalizeName(name) {
        return String(name || "")
            .trim()
            .toUpperCase()
            .replace(/[^A-Z0-9]+/g, "_")
            .replace(/^_+|_+$/g, "");
    }

    // Collect all possible aliases for an input field.
    function getAliases(input) {
        const aliases = [
            input.dataset.code,
            input.dataset.shortName,
            input.dataset.displayName,
            input.id,
            input.name
        ];

        const match = String(input.name || "").match(/^param_(\d+)$/i);

        if (match) {
            aliases.push("PARAM_" + match[1]);
        }

        return aliases.map(normalizeName).filter(Boolean);
    }

    // Read the current values entered by the user.
    function readValues() {
        const values = {};

        function addInput(input) {
            if (!input || String(input.value).trim() === "") {
                return;
            }

            const value = Number(input.value);

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

    // Safely evaluate basic arithmetic expressions.
    // Supports +, -, *, /, %, parentheses and decimals.
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

    // Replace formula variables with their corresponding numeric values.
    function calculateFormula(expression, values) {
        if (!expression) {
            return null;
        }

        let processed = String(expression)
            .replace(/×/g, "*")
            .replace(/÷/g, "/");

        const keys = Object.keys(values).sort(function (a, b) {
            return b.length - a.length;
        });

        keys.forEach(function (key) {
            const escaped = key.replace(
                /[.*+?^${}()|[\]\\]/g,
                "\\$&"
            );

            const pattern = new RegExp(
                "(?<![A-Z0-9_])" +
                escaped +
                "(?![A-Z0-9_])",
                "gi"
            );

            processed = processed.replace(
                pattern,
                String(values[key])
            );
        });

        // Do not calculate if any variable remains unresolved.
        if (/[A-Z_][A-Z0-9_]*/i.test(processed)) {
            return null;
        }

        return calculateExpression(processed);
    }

    // Recalculate formula fields whenever manual values change.
    function updateFormulaFields() {
        const values = readValues();

        let pending = formulaInputs.slice();
        let pass = 0;

        // Repeat passes to support formulas that depend on other formulas.
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

                // Make this calculated result available to dependent formulas.
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

        // Clear formulas whose required inputs are missing.
        pending.forEach(function (input) {
            input.value = "";
        });
    }

    // Listen for changes in manual result fields.
    manualInputs.forEach(function (input) {
        input.addEventListener("input", updateFormulaFields);
        input.addEventListener("change", updateFormulaFields);
    });

    // Calculate once when the page loads.
    updateFormulaFields();

    // Debug information for the browser console.
    console.info("[Formula Live] Initialized", {
        manualFields: manualInputs.length,
        formulaFields: formulaInputs.length,

        formulaExpressions: formulaInputs.map(function (input) {
            return {
                id: input.id,
                name: input.name,
                formula: input.dataset.formula,
                code: input.dataset.code
            };
        })
    });
});