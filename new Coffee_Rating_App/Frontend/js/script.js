// FastAPI backend URL
const API_URL = "http://127.0.0.1:8000";

// Get the HTML element where coffee cards will be displayed
const coffeeContainer = document.getElementById("coffee-container");


// --------------------------------------------------
// Load coffees when the page starts
// --------------------------------------------------

document.addEventListener("DOMContentLoaded", loadCoffees);


// --------------------------------------------------
// Get coffee data from the backend
// --------------------------------------------------

async function loadCoffees() {

    // Show loading message
    coffeeContainer.innerHTML =
        '<p class="loading-message">Loading coffees...</p>';

    try {

        // Send GET request to FastAPI
        const response = await fetch(`${API_URL}/coffees`);

        // Check whether the request was successful
        if (!response.ok) {
            throw new Error("Failed to load coffees");
        }

        // Convert response into JavaScript data
        const coffees = await response.json();

        // Display the coffee cards
        displayCoffees(coffees);

    } catch (error) {

        console.error("Error:", error);

        // Show user-friendly error message
        coffeeContainer.innerHTML = `
            <p class="error-message">
                Unable to load coffees.
                Please make sure the backend server is running.
            </p>
        `;
    }
}


// --------------------------------------------------
// Display coffee cards
// --------------------------------------------------

function displayCoffees(coffees) {

    // Remove the loading message
    coffeeContainer.innerHTML = "";


    // Check if there are no coffees
    if (coffees.length === 0) {

        coffeeContainer.innerHTML = `
            <p class="empty-message">
                No coffee categories available.
            </p>
        `;

        return;
    }


    // Create a card for each coffee
    coffees.forEach(function (coffee) {

        // Create the card
        const coffeeCard = document.createElement("div");

        coffeeCard.classList.add("coffee-card");


        // Create coffee name
        const coffeeName = document.createElement("h3");

        coffeeName.textContent = `☕ ${coffee.name}`;


        // Create vote count section
        const voteCount = document.createElement("p");

        voteCount.classList.add("vote-count");

        voteCount.innerHTML = `
            Votes:
            <span class="vote-number">
                ${coffee.votes}
            </span>
        `;


        // Create Vote button
        const voteButton = document.createElement("button");

        voteButton.textContent = "Vote";

        voteButton.classList.add("vote-button");


        // When the button is clicked
        voteButton.addEventListener("click", function () {

            voteForCoffee(
                coffee.id,
                voteCount,
                voteButton
            );

        });


        // Add elements to the card
        coffeeCard.appendChild(coffeeName);
        coffeeCard.appendChild(voteCount);
        coffeeCard.appendChild(voteButton);


        // Add card to the page
        coffeeContainer.appendChild(coffeeCard);

    });
}


// --------------------------------------------------
// Vote for a coffee
// --------------------------------------------------

async function voteForCoffee(
    coffeeId,
    voteCountElement,
    voteButton
) {

    // Disable button while request is processing
    voteButton.disabled = true;

    // Give the user simple visual feedback
    voteButton.textContent = "Voting...";


    try {

        // Send POST request to FastAPI
        const response = await fetch(
            `${API_URL}/coffees/${coffeeId}/vote`,
            {
                method: "POST"
            }
        );


        // Check if request was successful
        if (!response.ok) {
            throw new Error("Failed to vote");
        }


        // Get updated coffee information
        const updatedCoffee = await response.json();


        // Update only the vote count
        // No page reload is required
        voteCountElement.innerHTML = `
            Votes:
            <span class="vote-number">
                ${updatedCoffee.votes}
            </span>
        `;


    } catch (error) {

        console.error("Error:", error);

        alert(
            "Unable to submit your vote. Please try again."
        );

    } finally {

        // Enable button again
        voteButton.disabled = false;

        voteButton.textContent = "Vote";
    }
}