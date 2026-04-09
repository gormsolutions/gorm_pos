document.addEventListener("DOMContentLoaded", function () {
    // Handle the sign-up and sign-in panel toggling
    const container = document.getElementById("container");

    document.getElementById("signUp").addEventListener("click", () => {
        container.classList.add("right-panel-active");
    });

    document.getElementById("signIn").addEventListener("click", () => {
        container.classList.remove("right-panel-active");
    });

    document.getElementById("signUpLink").addEventListener("click", (e) => {
        e.preventDefault();
        container.classList.add("right-panel-active");
    });

    document.getElementById("signInLink").addEventListener("click", (e) => {
        e.preventDefault();
        container.classList.remove("right-panel-active");
    });

    // JavaScript to toggle password visibility for sign-up
    document.getElementById('toggleSignupPassword').addEventListener('click', function() {
        const signupPasswordInput = document.getElementById('signupPassword');
        if (signupPasswordInput) {
            const type = signupPasswordInput.type === 'password' ? 'text' : 'password';
            signupPasswordInput.type = type;
            this.textContent = type === 'password' ? '👁️' : '🙈'; // Change icon based on visibility
        }
    });

    // JavaScript to toggle password visibility for login
    document.getElementById('toggleLoginPassword').addEventListener('click', function() {
        const loginPasswordInput = document.getElementById('loginPassword');
        if (loginPasswordInput) {
            const type = loginPasswordInput.type === 'password' ? 'text' : 'password';
            loginPasswordInput.type = type;
            this.textContent = type === 'password' ? '👁️' : '🙈'; // Change icon based on visibility
        }
    });

    // Handle the login form submission
    document.getElementById("loginForm").addEventListener("submit", async (e) => {
        e.preventDefault(); // Prevent the default form submission

        const emailInput = e.target.querySelector('input[type="email"]');
        const passwordInput = e.target.querySelector('#loginPassword');  // Use the id selector for the password field

        console.log(emailInput, passwordInput);

        if (!emailInput || !passwordInput) {
            console.error("Email or Password input fields are not found.");
            alert("Please fill out all fields.");
            return;
        }

        const email = emailInput.value;
        const password = passwordInput.value;

        console.log(email, password);

        try {

            // Attempt to log out any existing session
            await fetch('/api/method/logout', {
                    method: "GET",
                    credentials: "include"
                });
    
                console.log("Logged out any existing session.");
                
            // Send a login request to the Frappe ERPNext API
            const response = await fetch(`/api/method/gormsolutions_mobile_app.custom_api.auth.login?usr=${encodeURIComponent(email)}&pwd=${encodeURIComponent(password)}`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            });

            const result = await response.json();
            console.log("API Response:", result); // Log the API response for debugging

            if (response.ok && result.message && result.message.sid) {
                // Store API credentials if needed (e.g., session storage for further requests)
                sessionStorage.setItem("sid", result.message.sid);
                sessionStorage.setItem("api_key", result.message.api_key);
                sessionStorage.setItem("api_secret", result.message.api_secret);

                // Redirect to the client portal on successful login
                window.location.href = "/app/home";
            } else {
                alert("Login failed. Please check your credentials.");
            }
        } catch (error) {
            console.error("Error during login:", error);
            alert("An error occurred. Please try again later.");
        }
    });

    // Handle the signup form submission
    document.getElementById("signupForm").addEventListener("submit", async (e) => {
        e.preventDefault(); // Prevent the default form submission

        const firstNameInput = e.target.querySelector('input[placeholder="Name"]');
        const emailInput = e.target.querySelector('input[type="email"]');
        const passwordInput = e.target.querySelector('input[placeholder="Password"]');

        if (!firstNameInput || !emailInput || !passwordInput) {
            console.error("One or more input fields are not found.");
            alert("Please fill out all fields.");
            return;
        }

        const firstName = firstNameInput.value;
        const email = emailInput.value;
        const password = passwordInput.value;

        try {
            // Fetch CSRF token
            const csrfResponse = await fetch('/api/method/gormsolutions_mobile_app.custom_api.auth.regenerate_session', {
                method: 'GET',
                credentials: 'include'
            });

            if (!csrfResponse.ok) {
                throw new Error("Failed to fetch CSRF token");
            }

            const csrfData = await csrfResponse.json();
            const csrfToken = csrfData.message.csrf_token;
            document.cookie = `X-Frappe-CSRF-Token=${csrfToken}; path=/`;

            // Send a signup request to the Frappe ERPNext API
            const response = await fetch("/api/method/gormsolutions_mobile_app.custom_api.auth.sign_up", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    'X-Frappe-CSRF-Token': csrfToken
                },
                body: JSON.stringify({ first_name: firstName, email: email, password: password })
            });

            const result = await response.json();
            console.log("API Response:", result.message.message); // Log the API response for debugging

            if (result.message.message === "User created successfully.") {
                alert(result.message.message); // Notify the user of success
                window.location.href = "/user_login"; // Redirect after signup
            } else {
                alert(result.message || "Signup failed. Please try again.");
            }
        } catch (error) {
            console.error("Error during signup:", error);
            alert("An error occurred. Please try again later.");
        }
    });
});
