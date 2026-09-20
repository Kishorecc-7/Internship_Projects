const profileForm = document.getElementById("profileForm");

const profileCard = document.getElementById("profileCard");

const statusMessage = document.getElementById("statusMessage");


profileForm.addEventListener("submit", async function (event) {

    event.preventDefault();

    const name = document.getElementById("name").value.trim();

    const bio = document.getElementById("bio").value.trim();

    const imageUrl = document.getElementById("imageUrl").value.trim();


    // Clear previous message
    statusMessage.textContent = "";
    statusMessage.className = "status-message";


    // Show loading
    statusMessage.textContent = "Creating profile...";
    statusMessage.classList.add("loading");


    try {

        console.log("Sending data to FastAPI...");

        console.log({
            name: name,
            bio: bio,
            image_url: imageUrl
        });


        // Send request to FastAPI
        const response = await fetch(
            "http://127.0.0.1:8000/profiles",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    name: name,
                    bio: bio,
                    image_url: imageUrl
                })
            }
        );


        console.log("Response status:", response.status);


        // Get response
        const data = await response.json();


        console.log("Response data:", data);


        // Backend returned an error
        if (!response.ok) {

            let errorMessage = "Unable to create profile.";

            if (data.detail) {

                if (Array.isArray(data.detail)) {

                    errorMessage = data.detail
                        .map(error => error.msg)
                        .join(", ");

                } else {

                    errorMessage = data.detail;
                }
            }


            throw new Error(errorMessage);
        }


        // Success
        statusMessage.className =
            "status-message success";

        statusMessage.textContent =
            "Profile created successfully!";


        // Display profile
        displayProfile(data);


        // Clear form
        profileForm.reset();

    }


    catch (error) {

        console.error("Error:", error);


        statusMessage.className =
            "status-message error";


        // IMPORTANT:
        // Show actual error instead of always saying
        // "Unable to connect to server"

        statusMessage.textContent =
            error.message;
    }

});


function displayProfile(profile) {

    // Clear old profile
    profileCard.innerHTML = "";


    // Create image
    const image = document.createElement("img");

    image.src = profile.image_url;

    image.alt = profile.name;

    image.className = "profile-image";


    // Broken image fallback
    image.onerror = function () {

        image.src =
            "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect width='100%25' height='100%25' fill='%23eeeeee'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%23666666'%3ENo Image%3C/text%3E%3C/svg%3E";

    };


    // Create name
    const name = document.createElement("h3");

    name.textContent = profile.name;


    // Create bio
    const bio = document.createElement("p");

    bio.textContent = profile.bio;


    // Create profile ID
    const id = document.createElement("small");

    id.textContent =
        `Profile ID: ${profile.id}`;


    // Create date
    const createdAt = document.createElement("small");

    const date = new Date(profile.created_at);

    createdAt.textContent =
        `Created: ${date.toLocaleString()}`;


    // Add elements
    profileCard.appendChild(image);

    profileCard.appendChild(name);

    profileCard.appendChild(bio);

    profileCard.appendChild(id);

    profileCard.appendChild(createdAt);
}