// ===============================
// Patient Registration JS
// ===============================

let totalAmount = 0;

// ----------------------------
// Add Test
// ----------------------------

function addTest(name, price) {

    // Prevent duplicate test
    if (document.getElementById("row_" + name.replace(/\s+/g, ""))) {
        return;
    }

    const selected = document.getElementById("selectedTests");

    // Remove "No tests selected."
    if (selected.innerHTML.includes("No tests selected")) {
        selected.innerHTML = "";
    }

    // Create selected test row
    const row = document.createElement("div");

    row.className =
        "selected-test d-flex justify-content-between align-items-center mb-2";

    row.id = "row_" + name.replace(/\s+/g, "");

   row.innerHTML = `
    <div class="flex-grow-1">

        <strong>${name}</strong><br>

        <small class="text-muted">
            Original Price : ₹${Number(price).toFixed(2)}
        </small>

        <div class="mt-2">

            <label class="small fw-bold">
                Patient Price
            </label>

            <input
                type="number"
                class="form-control form-control-sm patient-price"
                id="price_${name.replace(/\s+/g,'')}"
                value="${Number(price).toFixed(2)}"
                min="0"
                oninput="updatePrice('${name}', ${price})">

        </div>

    </div>

    <button
        type="button"
        class="btn btn-danger btn-sm ms-3"
        onclick="removeTest('${name}', ${price})">

        Remove

    </button>
`;

    selected.appendChild(row);
    console.log("Adding Test:", name);

console.log(document.getElementById("hiddenInputs"));

console.log(document.getElementById("patientForm"));

    // Hidden input for Flask
    const hidden = document.createElement("input");

    hidden.type = "hidden";
    hidden.name = "tests";
    hidden.value = name;
    const hiddenPrice = document.createElement("input");

hiddenPrice.type = "hidden";
hiddenPrice.name = "patient_price";
hiddenPrice.value = price;

hiddenPrice.id =
    "hiddenPrice_" + name.replace(/\s+/g,'');

document
    .getElementById("hiddenInputs")
    .appendChild(hiddenPrice);
    hidden.id = "hidden_" + name.replace(/\s+/g, "");

   const hiddenContainer = document.getElementById("hiddenInputs");

hiddenContainer.appendChild(hiddenPrice);
hiddenContainer.appendChild(hidden);

console.log("AFTER APPEND:");
console.log(hiddenContainer.innerHTML);

// alert(hiddenContainer.innerHTML);   // Delete or comment this line
    // Update total
calculateTotal();
}
// ----------------------------
// Remove Test
// ----------------------------

function removeTest(name, price) {

    const row = document.getElementById(
        "row_" + name.replace(/\s+/g, "")
    );

    if (row) {
        row.remove();
    }

    const hidden = document.getElementById(
        "hidden_" + name.replace(/\s+/g, "")
    );

    if (hidden) {
    hidden.remove();
}

const hiddenPrice = document.getElementById(
    "hiddenPrice_" + name.replace(/\s+/g,'')
);

if (hiddenPrice) {
    hiddenPrice.remove();
}

calculateTotal();

    const selected = document.getElementById("selectedTests");

    if (selected.children.length === 0) {

        selected.innerHTML =
            '<p class="text-muted">No tests selected.</p>';

    }

  calculatePayment();
}


// ----------------------------
// Payment Calculation
// ----------------------------

function calculatePayment() {

    let total =
        Number(document.getElementById("total_amount").value);

    let paid =
        Number(document.getElementById("paid_amount").value);

    if (paid < 0) {
        paid = 0;
    }

    if (paid > total) {
        paid = total;
        document.getElementById("paid_amount").value = paid;
    }

    let remaining = total - paid;

    document.getElementById("remaining_amount").value = remaining;

    let status = "Pending";

    if (paid === 0) {

        status = "Pending";

    }
    else if (remaining === 0) {

        status = "Paid";

    }
    else {

        status = "Partial";

    }

    document.getElementById("payment_status").value = status;

}
document
    .getElementById("paid_amount")
    .addEventListener("input", calculatePayment);
    // ===============================
// Live Search
// ===============================

const searchBox = document.getElementById("searchTest");

searchBox.addEventListener("input", function () {

    const value = this.value.trim().toLowerCase();

    document.querySelectorAll(".test-item").forEach(function(item){

        const testName =
            item.querySelector("h6")
                .textContent
                .trim()
                .toLowerCase();

        if(value === "" || testName.includes(value)){

            item.style.display = "flex";

        }else{

            item.style.display = "none";

        }

    });

});
// ===============================
// Reset Form
// ===============================

document.querySelector("button[type='reset']")
.addEventListener("click", function(){

    totalAmount = 0;

    document.getElementById("total_amount").value = 0;
    document.getElementById("paid_amount").value = 0;
    document.getElementById("remaining_amount").value = 0;
    document.getElementById("payment_status").value = "Pending";

    document.getElementById("selectedTests").innerHTML = `
        <p class="text-muted">
            No tests selected.
        </p>
    `;

    document.getElementById("hiddenInputs").innerHTML = "";

});
// ===============================
// Initial Page Load
// ===============================

function updatePrice(name) {

    const visiblePrice =
        document.getElementById(
            "price_" + name.replace(/\s+/g,'')
        ).value;

    const hiddenPrice =
        document.getElementById(
            "hiddenPrice_" + name.replace(/\s+/g,'')
        );

    hiddenPrice.value = visiblePrice;

  calculateTotal();
}
function calculateTotal() {

    let total = 0;

    document.querySelectorAll(".patient-price").forEach(function(input) {

        let price = parseFloat(input.value);

        if (!isNaN(price)) {
            total += price;
        }

    });

    document.getElementById("total_amount").value = total.toFixed(2);

    calculatePayment();

}
