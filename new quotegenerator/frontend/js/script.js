// ---------------------------------------
// FastAPI backend URL
// ---------------------------------------

const API_URL = "http://127.0.0.1:8000";


// ---------------------------------------
// Get HTML elements
// ---------------------------------------

const quoteText = document.getElementById("quote-text");

const quoteAuthor = document.getElementById("quote-author");

const generateButton = document.getElementById("generate-button");

const historyContainer =
    document.getElementById("history-container");

const errorMessage =
    document.getElementById("error-message");


// ---------------------------------------
// Load quote history when page loads
// ---------------------------------------

document.addEventListener("DOMContentLoaded", loadQuoteHistory);


// ---------------------------------------
// Generate Quote button
// ---------------------------------------

generateButton.addEventListener("click", generateQuote);


// ---------------------------------------
// Load previous quotes
// ---------------------------------------

async function loadQuoteHistory() {

    try {

        // Send GET request to the backend
        const response = await fetch(
            `${API_URL}/quotes`
        );


        // Check if request was successful
        if (!response.ok) {
            throw new Error("Failed to load quote history");
        }


        // Convert response to JavaScript data
        const quotes = await response.json();


        // Display the quotes
        displayQuoteHistory(quotes);

    } catch (error) {

        console.error(error);

        historyContainer.innerHTML = `
            <p class="empty-message">
                Unable to load quote history.
            </p>
        `;
    }
}


// ---------------------------------------
// Generate a new quote
// ---------------------------------------

async function generateQuote() {

    // Clear any previous error
    errorMessage.textContent = "";


    // Disable button
    generateButton.disabled = true;

    // Show loading feedback
    generateButton.textContent = "Generating...";


    try {

        // Request a new quote
        const response = await fetch(
            `${API_URL}/quote`
        );


        // Check if request was successful
        if (!response.ok) {
            throw new Error("Failed to generate quote");
        }


        // Convert response to JavaScript object
        const newQuote = await response.json();


        // Display the quote in the main card
        displayMainQuote(newQuote);


        // Add the new quote to the beginning
        // of the history list
        addQuoteToHistory(newQuote);

    } catch (error) {

        console.error(error);

        // Show user-friendly error
        errorMessage.textContent =
            "Unable to generate a quote. Please try again.";

    } finally {

        // Enable button again
        generateButton.disabled = false;

        generateButton.textContent = "Generate Quote";
    }
}


// ---------------------------------------
// Display quote in the main quote card
// ---------------------------------------

function displayMainQuote(quote) {

    quoteText.textContent = `“${quote.quote}”`;

    quoteAuthor.textContent = `— ${quote.author}`;
}


// ---------------------------------------
// Display quote history
// ---------------------------------------

function displayQuoteHistory(quotes) {

    // Clear existing history
    historyContainer.innerHTML = "";


    // Check whether history is empty
    if (quotes.length === 0) {

        historyContainer.innerHTML = `
            <p class="empty-message">
                No quotes generated yet.
            </p>
        `;

        return;
    }


    // Display newest quotes first
    const newestFirst = [...quotes].reverse();


    newestFirst.forEach(function (quote) {

        const historyCard =
            createHistoryCard(quote);

        historyContainer.appendChild(historyCard);
    });
}


// ---------------------------------------
// Add a newly generated quote
// to the beginning of history
// ---------------------------------------

function addQuoteToHistory(quote) {

    // Remove "No quotes generated yet."
    // or other initial content
    if (
        historyContainer.textContent.trim() ===
        "No quotes generated yet."
    ) {
        historyContainer.innerHTML = "";
    }


    const historyCard =
        createHistoryCard(quote);


    // Add newest quote at the top
    historyContainer.prepend(historyCard);
}


// ---------------------------------------
// Create one history card
// ---------------------------------------

function createHistoryCard(quote) {

    const historyCard =
        document.createElement("div");

    historyCard.classList.add("history-card");


    // Quote text
    const quoteElement =
        document.createElement("p");

    quoteElement.classList.add("history-quote");

    quoteElement.textContent =
        `“${quote.quote}”`;


    // Author
    const authorElement =
        document.createElement("p");

    authorElement.classList.add("history-author");

    authorElement.textContent =
        `— ${quote.author}`;


    // Add elements to card
    historyCard.appendChild(quoteElement);

    historyCard.appendChild(authorElement);


    return historyCard;
}