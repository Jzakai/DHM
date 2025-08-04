document.addEventListener("DOMContentLoaded", () => {
    const paramsForm = document.getElementById("params-form");

    paramsForm.addEventListener("submit", async (e) => {
        e.preventDefault();

        // --- Collect parameters from HTML input fields ---
        const params = {
            wavelength: parseFloat(document.getElementById("wavelength").value),
            pixel_size: parseFloat(document.getElementById("pixel_size").value),
            magnification: parseFloat(document.getElementById("magnification").value),
            delta_ri: parseFloat(document.getElementById("delta_ri").value),
            dc_remove: parseInt(document.getElementById("dc_remove").value),
            filter_type: document.getElementById("filter_type").value,
            filter_size: parseInt(document.getElementById("filter_size").value),
            beam_type: document.getElementById("beam_type").value,
            threshold_strength: parseFloat(document.getElementById("threshold_strength").value)
        };

        try {
            // --- Send parameters to FastAPI ---
            const response = await fetch("http://127.0.0.1:8000/set_params", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(params)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }

            const result = await response.json();
            console.log("Server Response:", result);

            // --- Call run_phase_difference after parameters are set ---
            const phaseResponse = await fetch("http://127.0.0.1:8000/run_phase_difference", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(params) // send same params for now
            });

            if (!phaseResponse.ok) {
                throw new Error(`HTTP error! Status: ${phaseResponse.status}`);
            }

            const phaseData = await phaseResponse.json();
            console.log("Phase Map Data:", phaseData.phase_map);

            alert("Phase difference computed successfully!");

        } catch (error) {
            console.error("Error communicating with server:", error);
            alert("Error: " + error.message);
        }
    });
});
