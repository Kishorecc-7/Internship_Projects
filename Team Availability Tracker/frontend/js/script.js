// Backend API URL
const API_URL = "http://127.0.0.1:8000";


// Get HTML elements
const teamList = document.getElementById("team-list");
const loadingMessage = document.getElementById("loading-message");
const emptyMessage = document.getElementById("empty-message");
const errorMessage = document.getElementById("error-message");

const totalMembers = document.getElementById("total-members");
const availableMembers = document.getElementById("available-members");
const awayMembers = document.getElementById("away-members");


// Store team members in JavaScript
let users = [];


// =========================
// Load Team Members
// =========================

async function loadUsers() {

    try {

        loadingMessage.classList.remove("hidden");
        emptyMessage.classList.add("hidden");

        const response = await fetch(`${API_URL}/users`);

        if (!response.ok) {
            throw new Error("Unable to load users");
        }

        users = await response.json();

        loadingMessage.classList.add("hidden");

        if (users.length === 0) {

            emptyMessage.classList.remove("hidden");

            updateSummary();

            return;
        }

        renderUsers();

        updateSummary();

    } catch (error) {

        loadingMessage.classList.add("hidden");

        showError("Unable to load team members. Please try again.");
    }
}


// =========================
// Render Users
// =========================

function renderUsers() {

    teamList.innerHTML = "";

    users.forEach(function(user) {

        const card = createUserCard(user);

        teamList.appendChild(card);

    });
}


// =========================
// Create User Card
// =========================

function createUserCard(user) {

    // Create main card
    const card = document.createElement("div");

    card.className = "team-card";

    card.dataset.userId = user.id;


    // Get user's initials
    const initials = getInitials(user.name);


    // Create member information
    const memberInfo = document.createElement("div");

    memberInfo.className = "member-info";


    // Avatar
    const avatar = document.createElement("div");

    avatar.className = "avatar";

    avatar.textContent = initials;


    // Member details
    const memberDetails = document.createElement("div");

    memberDetails.className = "member-details";


    const name = document.createElement("h3");

    name.className = "member-name";

    name.textContent = user.name;


    const department = document.createElement("p");

    department.className = "member-department";

    department.textContent = user.department;


    memberDetails.appendChild(name);
    memberDetails.appendChild(department);

    memberInfo.appendChild(avatar);
    memberInfo.appendChild(memberDetails);


    // Availability area
    const availabilityArea = document.createElement("div");

    availabilityArea.className = "availability-area";


    // Status
    const status = document.createElement("div");

    updateStatusElement(status, user.available);


    // Toggle
    const toggleLabel = document.createElement("label");

    toggleLabel.className = "toggle";


    const checkbox = document.createElement("input");

    checkbox.type = "checkbox";

    checkbox.checked = user.available;


    const slider = document.createElement("span");

    slider.className = "slider";


    toggleLabel.appendChild(checkbox);
    toggleLabel.appendChild(slider);


    // Listen for toggle changes
    checkbox.addEventListener("change", function() {

        updateAvailability(
            user.id,
            checkbox.checked,
            checkbox,
            status
        );

    });


    availabilityArea.appendChild(status);
    availabilityArea.appendChild(toggleLabel);


    // Add everything to card
    card.appendChild(memberInfo);
    card.appendChild(availabilityArea);


    return card;
}


// =========================
// Update Status Display
// =========================

function updateStatusElement(statusElement, available) {

    statusElement.className = "status";


    const dot = document.createElement("span");

    dot.className = "status-dot";


    const text = document.createElement("span");


    if (available) {

        statusElement.classList.add("available");

        text.textContent = "Available";

    } else {

        statusElement.classList.add("away");

        text.textContent = "Away";
    }


    statusElement.appendChild(dot);
    statusElement.appendChild(text);
}


// =========================
// Update Availability
// =========================

async function updateAvailability(
    userId,
    newAvailability,
    checkbox,
    statusElement
) {

    // Find the user
    const user = users.find(function(item) {
        return item.id === userId;
    });


    if (!user) {
        return;
    }


    // Store previous value
    const previousAvailability = user.available;


    // Temporarily disable toggle
    checkbox.disabled = true;


    try {

        const response = await fetch(
            `${API_URL}/users/${userId}/availability`,
            {
                method: "PATCH",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    available: newAvailability
                })
            }
        );


        if (!response.ok) {
            throw new Error("Unable to update availability");
        }


        // Get updated user from backend
        const updatedUser = await response.json();


        // Update local user data
        user.available = updatedUser.available;


        // Update status
        updateStatusElement(
            statusElement,
            updatedUser.available
        );


        // Update summary counts
        updateSummary();


        // Hide any previous error
        hideError();

    } catch (error) {

        // Restore previous toggle value
        checkbox.checked = previousAvailability;


        // Restore previous status
        updateStatusElement(
            statusElement,
            previousAvailability
        );


        showError(
            "Unable to update availability. Please try again."
        );

    } finally {

        // Enable toggle again
        checkbox.disabled = false;
    }
}


// =========================
// Update Summary
// =========================

function updateSummary() {

    const total = users.length;


    let available = 0;


    users.forEach(function(user) {

        if (user.available === true) {
            available++;
        }

    });


    const away = total - available;


    totalMembers.textContent = total;

    availableMembers.textContent = available;

    awayMembers.textContent = away;
}


// =========================
// Get User Initials
// =========================

function getInitials(name) {

    const nameParts = name.trim().split(" ");


    if (nameParts.length === 1) {

        return nameParts[0]
            .substring(0, 2)
            .toUpperCase();
    }


    const firstInitial = nameParts[0][0];

    const lastInitial = nameParts[nameParts.length - 1][0];


    return (
        firstInitial + lastInitial
    ).toUpperCase();
}


// =========================
// Show Error
// =========================

function showError(message) {

    errorMessage.textContent = message;

    errorMessage.classList.remove("hidden");
}


// =========================
// Hide Error
// =========================

function hideError() {

    errorMessage.classList.add("hidden");
}


// =========================
// Load Users When Page Opens
// =========================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadUsers();

    }
);