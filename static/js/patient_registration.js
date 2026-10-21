// ==========================================
// Patient Registration JS
// FIXED: Test ID instead of Test Name
// ==========================================

let totalAmount = 0;


// ==========================================
// Helper: Create a safe DOM ID
// ==========================================

function getSafeTestId(testId) {
    return String(testId).trim().replace(/[^a-zA-Z0-9_-]/g, "_");
}


// ==========================================
// Add Test
// ==========================================

function addTest(testId, name, price) {

    testId = String(testId).trim();
    price = Number(price);

    if (
        !testId ||
        !/^\d+$/.test(testId) ||
        !Number.isFinite(price) ||
        price < 0
    ) {
        console.error("Invalid test details:", {
            testId: testId,
            name: name,
            price: price
        });

        alert("Invalid test details. Please refresh the page and try again.");
        return;
    }

    const safeId = getSafeTestId(testId);

    // Prevent duplicate selection
    if (document.getElementById("row_" + safeId)) {
        return;
    }

    const selectedTests = document.getElementById("selectedTests");

    if (!selectedTests) {
        console.error("Selected tests container not found.");
        return;
    }

    if (selectedTests.innerText.includes("No tests selected")) {
        selectedTests.innerHTML = "";
    }

    // Create selected test row
    const row = document.createElement("div");

    row.id = "row_" + safeId;

    row.className =
        "selected-test d-flex justify-content-between align-items-start border rounded p-2 mb-2";

    row.innerHTML = `
        <div class="flex-grow-1">

            <strong class="test-name"></strong>

            <br>

            <small class="text-muted">
                Original Price: ₹${price.toFixed(2)}
            </small>

            <div class="mt-2">

                <label class="small fw-bold">
                    Patient Price
                </label>

                <input
                    type="number"
                    class="form-control form-control-sm patient-price"
                    id="price_${safeId}"
                    value="${price.toFixed(2)}"
                    min="0"
                    step="0.01">

            </div>

        </div>

        <button
            type="button"
            class="btn btn-danger btn-sm ms-3 remove-btn">
            Remove
        </button>
    `;

    // Safely display test name
    row.querySelector(".test-name").textContent = name;

    selectedTests.appendChild(row);

    // ==========================================
    // Hidden Inputs
    // ==========================================

    const hiddenContainer = document.getElementById("hiddenInputs");

    if (!hiddenContainer) {
        row.remove();
        console.error("Hidden inputs container not found.");
        return;
    }

    // Hidden Test ID
    const hiddenTest = document.createElement("input");

    hiddenTest.type = "hidden";
    hiddenTest.name = "tests";
    hiddenTest.value = testId;
    hiddenTest.id = "hidden_" + safeId;

    // Hidden Patient Price
    const hiddenPrice = document.createElement("input");

    hiddenPrice.type = "hidden";
    hiddenPrice.name = "patient_price";
    hiddenPrice.value = price.toFixed(2);
    hiddenPrice.id = "hiddenPrice_" + safeId;

    hiddenContainer.appendChild(hiddenTest);
    hiddenContainer.appendChild(hiddenPrice);

    // ==========================================
    // Patient Price Change
    // ==========================================

    row.querySelector(".patient-price").addEventListener(
        "input",
        function () {

            hiddenPrice.value = this.value;

            calculateTotal();

        }
    );

    // ==========================================
    // Remove Button
    // ==========================================

    row.querySelector(".remove-btn").addEventListener(
        "click",
        function () {

            removeTest(testId);

        }
    );

    calculateTotal();
}


// ==========================================
// Remove Test
// ==========================================

function removeTest(testId) {

    const safeId = getSafeTestId(testId);

    // Remove selected test row
    const row = document.getElementById("row_" + safeId);

    if (row) {
        row.remove();
    }

    // Remove hidden Test ID
    const hiddenTest = document.getElementById("hidden_" + safeId);

    if (hiddenTest) {
        hiddenTest.remove();
    }

    // Remove hidden price
    const hiddenPrice = document.getElementById("hiddenPrice_" + safeId);

    if (hiddenPrice) {
        hiddenPrice.remove();
    }

    // Display empty selection message
    const selectedTests = document.getElementById("selectedTests");

    if (selectedTests && selectedTests.children.length === 0) {

        selectedTests.innerHTML = `
            <p class="text-muted">
                No tests selected.
            </p>
        `;

    }

    calculateTotal();
}


// ==========================================
// Calculate Total
// ==========================================

function calculateTotal() {

    let total = 0;

    document.querySelectorAll(".patient-price").forEach(
        function (input) {

            const price = parseFloat(input.value);

            if (Number.isFinite(price) && price >= 0) {
                total += price;
            }

        }
    );

    totalAmount = total;

    const totalInput = document.getElementById("total_amount");

    if (totalInput) {
        totalInput.value = total.toFixed(2);
    }

    calculatePayment();
}


// ==========================================
// Calculate Payment
// ==========================================

function calculatePayment() {

    const totalInput = document.getElementById("total_amount");
    const paidInput = document.getElementById("paid_amount");
    const remainingInput = document.getElementById("remaining_amount");
    const statusInput = document.getElementById("payment_status");

    if (!totalInput || !paidInput || !remainingInput || !statusInput) {
        return;
    }

    const total = parseFloat(totalInput.value) || 0;

    let paid = parseFloat(paidInput.value) || 0;

    // Prevent negative payment
    if (paid < 0) {
        paid = 0;
        paidInput.value = "0.00";
    }

    // Prevent payment greater than total
    if (paid > total) {
        paid = total;
        paidInput.value = paid.toFixed(2);
    }

    // Calculate remaining amount
    const remaining = Math.max(0, total - paid);

    remainingInput.value = remaining.toFixed(2);

    // Payment status
    let status = "Pending";

    if (total > 0 && remaining === 0) {
        status = "Paid";
    } else if (paid > 0) {
        status = "Partial";
    }

    statusInput.value = status;

    updateUPIPayment();
}


// ==========================================
// Initialize UPI Payment
// ==========================================

function initializeUPIPayment() {

    const paymentMode = document.getElementById("payment_mode");

    if (!paymentMode) {
        return;
    }

    paymentMode.addEventListener("change", function () {
        updateUPIPayment();
    });

    updateUPIPayment();
}


// ==========================================
// Update UPI Payment
// ==========================================

function updateUPIPayment() {

    const paymentMode = document.getElementById("payment_mode");

    const upiSection = document.getElementById("upiPaymentSection");

    const qrImage = document.getElementById("upiQrImage");

    const qrLoading = document.getElementById("upiQrLoading");

    const amountDisplay = document.getElementById("upiDisplayAmount");

    const statusDisplay = document.getElementById("upiPaymentStatus");

    if (!paymentMode || !upiSection) {
        return;
    }

    // Hide UPI section for other payment modes
    if (paymentMode.value !== "UPI") {

        upiSection.style.display = "none";

        return;
    }

    upiSection.style.display = "block";

    const total = parseFloat(
        document.getElementById("total_amount")?.value
    ) || 0;

    const paid = parseFloat(
        document.getElementById("paid_amount")?.value
    ) || 0;

    /*
     * Existing behavior preserved:
     * QR amount is based on the Paid Amount field.
     */

    const qrAmount = paid;

    // No amount entered
    if (qrAmount <= 0) {

        if (qrImage) {
            qrImage.src = "";
            qrImage.style.display = "none";
        }

        if (qrLoading) {

            qrLoading.style.display = "block";

            qrLoading.innerHTML = `
                <i class="fas fa-qrcode fa-3x mb-3"></i>

                <p class="mb-0">
                    Enter the payment amount to generate QR Code.
                </p>
            `;
        }

        if (amountDisplay) {
            amountDisplay.innerText = "₹0.00";
        }

        if (statusDisplay) {
            statusDisplay.innerText = "Waiting for payment";
        }

        return;
    }

    // Display QR amount
    if (amountDisplay) {
        amountDisplay.innerText = "₹" + qrAmount.toFixed(2);
    }

    if (statusDisplay) {
        statusDisplay.innerText = "Waiting for payment";
    }

    if (qrImage) {
        qrImage.style.display = "none";
    }

    if (qrLoading) {

        qrLoading.style.display = "block";

        qrLoading.innerHTML = `
            <div
                class="spinner-border text-success mb-3"
                role="status">
            </div>

            <p class="mb-0">
                Generating QR Code...
            </p>
        `;
    }

    const note = "Laboratory Payment";

    const qrUrl =
        "/generate-upi-qr"
        + "?amount=" + encodeURIComponent(qrAmount.toFixed(2))
        + "&note=" + encodeURIComponent(note)
        + "&_=" + Date.now();

    console.log("Generating UPI QR:", qrUrl);

    if (!qrImage) {
        console.error("upiQrImage element not found.");
        return;
    }

    qrImage.onload = function () {

        qrImage.style.display = "block";

        if (qrLoading) {
            qrLoading.style.display = "none";
        }

        if (statusDisplay) {
            statusDisplay.innerText = "Ready for payment";
        }
    };

    qrImage.onerror = function () {

        console.error("UPI QR generation failed.");

        qrImage.style.display = "none";

        if (qrLoading) {

            qrLoading.style.display = "block";

            qrLoading.innerHTML = `
                <i class="fas fa-exclamation-triangle text-danger fa-3x mb-3"></i>

                <p class="text-danger fw-bold mb-1">
                    Unable to generate QR Code
                </p>

                <small class="text-muted">
                    Check Flask terminal for the error.
                </small>
            `;
        }

        if (statusDisplay) {
            statusDisplay.innerText = "QR generation failed";
        }
    };

    qrImage.src = qrUrl;
}


// ==========================================
// Live Search
// ==========================================

function initializeSearch() {

    const searchBox = document.getElementById("searchTest");

    if (!searchBox) {
        return;
    }

    searchBox.addEventListener("input", function () {

        const keyword = this.value.trim().toLowerCase();

        document.querySelectorAll("#testList .test-item").forEach(
            function (item) {

                const testName = item.querySelector("h6")
                    ?.textContent.trim().toLowerCase() || "";

                if (testName.includes(keyword)) {
                    item.classList.remove("d-none");
                } else {
                    item.classList.add("d-none");
                }

            }
        );

    });
}


// ==========================================
// Reset Form
// ==========================================

function initializeReset() {

    const resetBtn = document.querySelector("button[type='reset']");

    if (!resetBtn) {
        return;
    }

    resetBtn.addEventListener("click", function () {

        // Allow browser reset first
        setTimeout(function () {

            totalAmount = 0;

            const selectedTests = document.getElementById("selectedTests");

            if (selectedTests) {
                selectedTests.innerHTML = `
                    <p class="text-muted">
                        No tests selected.
                    </p>
                `;
            }

            const hiddenInputs = document.getElementById("hiddenInputs");

            if (hiddenInputs) {
                hiddenInputs.innerHTML = "";
            }

            const totalInput = document.getElementById("total_amount");
            const paidInput = document.getElementById("paid_amount");
            const remainingInput = document.getElementById("remaining_amount");
            const statusInput = document.getElementById("payment_status");

            if (totalInput) totalInput.value = "0.00";
            if (paidInput) paidInput.value = "0.00";
            if (remainingInput) remainingInput.value = "0.00";
            if (statusInput) statusInput.value = "Pending";

            const upiSection = document.getElementById("upiPaymentSection");

            if (upiSection) {
                upiSection.style.display = "none";
            }

            const qrImage = document.getElementById("upiQrImage");

            if (qrImage) {
                qrImage.src = "";
                qrImage.style.display = "none";
            }

            const qrLoading = document.getElementById("upiQrLoading");

            if (qrLoading) {

                qrLoading.style.display = "block";

                qrLoading.innerHTML = `
                    <i class="fas fa-qrcode fa-3x mb-3"></i>

                    <p class="mb-0">
                        QR Code will appear here
                    </p>
                `;
            }

            const amountDisplay = document.getElementById("upiDisplayAmount");

            if (amountDisplay) {
                amountDisplay.innerText = "₹0.00";
            }

            const statusDisplay = document.getElementById("upiPaymentStatus");

            if (statusDisplay) {
                statusDisplay.innerText = "Waiting for payment";
            }

            updateUPIPayment();

        }, 0);

    });
}


// ==========================================
// Payment Input
// ==========================================

function initializePayment() {

    const paidInput = document.getElementById("paid_amount");

    if (!paidInput) {
        return;
    }

    paidInput.addEventListener("input", calculatePayment);
}


// ==========================================
// Add Button Events
// ==========================================

function initializeButtons() {

    document.querySelectorAll(".add-test-btn").forEach(
        function (btn) {

            btn.addEventListener("click", function () {

                const testId = this.dataset.id;

                const testName = this.dataset.name;

                const testPrice = parseFloat(this.dataset.price);

                if (!testId || !testName || !Number.isFinite(testPrice)) {

                    console.error("Invalid test data:", {
                        id: testId,
                        name: testName,
                        price: testPrice
                    });

                    alert(
                        "Unable to add this test. Please refresh the page and try again."
                    );

                    return;
                }

                addTest(testId, testName, testPrice);

            });

        }
    );
}


// ==========================================
// Initial Load
// ==========================================

document.addEventListener("DOMContentLoaded", function () {

    initializeButtons();

    initializeSearch();

    initializeReset();

    initializePayment();

    initializeUPIPayment();

    calculatePayment();

});