let image = {
    psi: null
};


let point1 = null;
let point2 = null;

document.addEventListener("DOMContentLoaded", function () {
    let stream = null;
    const video = document.getElementById("video");
    const padStatus = document.getElementById("pad-status");

    let selectingROI = false;
    let startX, startY, endX, endY;

    const roiCanvas = document.getElementById("roiCanvas");
    const ctx = roiCanvas.getContext("2d");
    const phaseImage = document.getElementById("phaseImage");

    document.getElementById("openCam").addEventListener("click", async () => {
        try {
            stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            video.srcObject = stream;
        } catch (e) {
            alert("Could not open camera: " + e.message);
        }
    });

    document.getElementById("stopCam").addEventListener("click", () => {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            video.srcObject = null;
            stream = null;
        }
    });

    document.getElementById("imageFile").addEventListener("change", () => console.log("Object image selected"));
    document.getElementById("refFile").addEventListener("change", () => console.log("Reference image selected"));

    document.getElementById("checkSpectrum").addEventListener("click", () => alert("Check Spectrum clicked"));
    document.getElementById("phaseDiff").addEventListener("click", (e) => { e.preventDefault(); sendParams(); });
    document.getElementById("selectRoiBtn").addEventListener("click", startROISelection);
    document.getElementById("3dbtn").addEventListener("click", fetch3DPlot);
    document.getElementById("runAll").addEventListener("click", () => alert("Run All sequence started"));
    document.getElementById("2dbtn").addEventListener("click", () => alert("2dbtn clicked"));
    document.getElementById("1dbtn").addEventListener("click", startPointsSelection);
    document.getElementById('mainGallery').addEventListener('click', () => {
        const details = document.getElementById('outputImages');
        details.style.display = (details.style.display === 'flex') ? 'none' : 'flex';
    });

});

async function selectROI(x1, y1, x2, y2) {
    try {
        const response = await fetch("http://192.168.1.121:8000/select_roi", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x1, y1, x2, y2 })
        });
        const data = await response.json();
        if (data.error) {
            alert(data.error);
        } else {
            alert("ROI selected and noise reduced!");
        }
    } catch (error) {
        console.error("Error selecting ROI:", error);
        alert("Error selecting ROI: " + error.message);
    }
}



function startROISelection() {
    if (!image.psi) {
        alert("No phase difference image available.");
        return;
    }

    const popup = window.open('', 'ImagePopup', 'width=800,height=600');
    popup.document.write(`
            <html>
            <head>
            <title>Select ROI</title>
            <style>
                body { margin: 0; }
                canvas { display: block; cursor: crosshair; }
            </style>
            </head>
            <body>
            <canvas id="canvas"></canvas>
            <script>
                const canvas = document.getElementById('canvas');
                const ctx = canvas.getContext('2d');
                const img = new Image();
                img.src = "data:image/png;base64,${image.psi}";
                
                let startX, startY, endX, endY, drawing = false;

                img.onload = function() {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
                };

                canvas.addEventListener('mousedown', e => {
                const rect = canvas.getBoundingClientRect();
                startX = e.clientX - rect.left;
                startY = e.clientY - rect.top;
                drawing = true;
                });

                canvas.addEventListener('mousemove', e => {
                if (!drawing) return;
                const rect = canvas.getBoundingClientRect();
                endX = e.clientX - rect.left;
                endY = e.clientY - rect.top;
                ctx.drawImage(img, 0, 0);
                ctx.strokeStyle = 'red';
                ctx.lineWidth = 2;
                ctx.strokeRect(startX, startY, endX - startX, endY - startY);
                });

                canvas.addEventListener('mouseup', e => {
                drawing = false;
                const rect = canvas.getBoundingClientRect();
                endX = e.clientX - rect.left;
                endY = e.clientY - rect.top;
                const coords = {
                    x1: Math.round(Math.min(startX, endX)),
                    y1: Math.round(Math.min(startY, endY)),
                    x2: Math.round(Math.max(startX, endX)),
                    y2: Math.round(Math.max(startY, endY))
                };
                window.opener.receiveROI(coords);
                setTimeout(() => window.close(), 500);
                });
            <\/script>
            </body>
            </html>
            `);
}

function receiveROI(coords) {
    console.log("Selected ROI:", coords);
    selectROI(coords.x1, coords.y1, coords.x2, coords.y2);
}

// Directional pad logic
const quads = document.querySelectorAll(".quad");
const center = document.querySelector(".center");

function highlight(dir) {
    quads.forEach(q => q.classList.toggle("active", q.dataset.dir === dir));
}

quads.forEach(q => {
    q.addEventListener("click", () => {
        const d = q.dataset.dir;
        padStatus.textContent = `Direction: ${d}`;
        highlight(d);
        // TODO: send command to backend or move stage
        console.log("Clicked", d);
    });
});

center.addEventListener("click", () => {
    padStatus.textContent = "Home";
    highlight(null);
    console.log("Home pressed");
});


async function sendParams() {
    const formData = new FormData();
    formData.append("wavelength", document.getElementById("wavelength").value);
    formData.append("pixel_size", document.getElementById("pixelSize").value);
    formData.append("magnification", document.getElementById("magnification").value);
    formData.append("delta_ri", document.getElementById("ri").value);
    formData.append("dc_remove", document.getElementById("skipPixels").value);
    formData.append("filter_type", document.getElementById("filterType").value);
    formData.append("filter_size", document.getElementById("filterSize").value);
    formData.append("beam_type", document.getElementById("beams").value);
    formData.append("threshold_strength", "1.0");

    const imageFile = document.getElementById("imageFile").files[0];
    const refFile = document.getElementById("refFile").files[0];
    if (!imageFile || !refFile) {
        alert("Please select both image and reference files.");
        return;
    }
    formData.append("image", imageFile);
    formData.append("reference", refFile);

    try {
        const response = await fetch("http://192.168.1.121:8000/run_phase_difference", {
            method: "POST",
            body: formData
        });
        if (!response.ok) throw new Error("Server error " + response.status);

        const data = await response.json();

        // Inject the phase difference image into #phaseOutput
        const phaseOutputBox = document.getElementById("phaseOutput");
        phaseOutputBox.innerHTML = `
            <span>Phase Difference</span>
            <img src="data:image/png;base64,${data.phase_image}" 
                 alt="Phase Difference" 
                 style="max-width:100%; display:block; margin-top:8px; border:1px solid #ccc;">
        `;

        // Optional: log details
        console.log("Phase shape:", data.shape);
        console.log("Phase range:", data.min, "to", data.max);
        image.psi = data.phase_image;

        alert("Phase difference computed and displayed!");
    } catch (error) {
        console.error("Error:", error);
        alert("Error: " + error.message);
    }
}




async function selectPoints(x1, y1, x2, y2) {
    try {
        const response = await fetch("http://192.168.1.121:8000/compute_1d", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x1, y1, x2, y2 })
        });
        const data = await response.json();
        if (data.error) {
            alert(data.error);
        } else {
            alert("line selected");
        }
    } catch (error) {
        console.error("Error selecting line:", error);
        alert("Error selecting line: " + error.message);
    }
}


function startPointsSelection() {
    if (!image.psi) {
        alert("No phase difference image available.");
        return;
    }

    const popup = window.open('', 'ImagePopup', 'width=800,height=600');
    if (!popup) {
        alert("Popup blocked");
        return;
    }

    popup.document.write(`
        <html>
        <head>
        <title>Select Line</title>
        <style>
            body { margin: 0; }
            canvas { display: block; cursor: crosshair; }
        </style>
        </head>
        <body>
        <canvas id="canvas"></canvas>
        <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();
            img.src = "data:image/png;base64,${image.psi}";

            let clickCount = 0;
            let point1 = null;
            let point2 = null;

            img.onload = function() {
                canvas.width = img.width;
                canvas.height = img.height;
                ctx.drawImage(img, 0, 0);
            };

            canvas.addEventListener('click', e => {
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                clickCount++;

                if (clickCount === 1) {
                    point1 = { x: Math.round(x), y: Math.round(y) };
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);
                    ctx.beginPath();
                    ctx.arc(point1.x, point1.y, 5, 0, 2 * Math.PI);
                    ctx.fillStyle = 'red';
                    ctx.fill();
                } else if (clickCount === 2) {
                    point2 = { x: Math.round(x), y: Math.round(y) };
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);
                    ctx.beginPath();
                    ctx.moveTo(point1.x, point1.y);
                    ctx.lineTo(point2.x, point2.y);
                    ctx.strokeStyle = 'red';
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    window.opener.receivePoints({ 
                        x1: point1.x, y1: point1.y, x2: point2.x, y2: point2.y 
                    });
                    setTimeout(() => window.close(), 300);
                } else {
                    clickCount = 1;
                    point1 = { x: Math.round(x), y: Math.round(y) };
                    point2 = null;
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.drawImage(img, 0, 0);
                    ctx.beginPath();
                    ctx.arc(point1.x, point1.y, 5, 0, 2 * Math.PI);
                    ctx.fillStyle = 'red';
                    ctx.fill();
                }
            });
        <\/script>
        </body>
        </html>
    `);
}



// Global variables to receive points from popup

function receivePoints(coords) {
    console.log("Selected Points (raw):", coords);
    selectPoints(coords.x1, coords.y1, coords.x2, coords.y2);
}



async function fetch3DPlot() {
    try {
        const response = await fetch("http://192.168.1.121:8000/compute_3d");
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        const output3D = document.getElementById("output3D");
        output3D.innerHTML = `<span>3D</span><div id="plot3d" style="height:400px;"></div>`;

        Plotly.newPlot('plot3d', [{
            type: 'surface',
            x: data.x,
            y: data.y,
            z: data.z,
            colorscale: 'Jet'
        }], {
            scene: {
                xaxis: { title: 'X (μm)' },
                yaxis: { title: 'Y (μm)' },
                zaxis: { title: 'Thickness (μm)' }
            },
            margin: { l: 0, r: 0, b: 0, t: 0 }
        });
    } catch (error) {
        console.error("Error:", error);
        alert("Error: " + error.message);
    }
}



document.getElementById('mainGallery').addEventListener('click', () => {
    const details = document.getElementById('outputImages');
    if (details.style.display === 'flex') {
        details.style.display = 'none';
    } else {
        details.style.display = 'flex';
    }
});