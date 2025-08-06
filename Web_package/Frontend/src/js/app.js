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

// Placeholder wiring for other buttons:
document.getElementById("imageFile").addEventListener("change", () => {
  console.log("Object image selected");
});

document.getElementById("refFile").addEventListener("change", () => {
  console.log("Reference image selected");
});

document.getElementById("checkSpectrum").addEventListener("click", () => {
  alert("Check Spectrum clicked");
});

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("phaseDiff").addEventListener("click", (e) => {
        e.preventDefault();
        sendParams();
    });
});

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("selectRoiBtn").addEventListener("click", startROISelection);
    document.getElementById("3dbtn").addEventListener("click", fetch3DPlot);
});


document.getElementById("runAll").addEventListener("click", () => {
  alert("Run All sequence started");
});

document.getElementById("2dbtn").addEventListener("click", () => {
  alert("2dbtn clicked");
});



document.getElementById("1dbtn").addEventListener("click", () => {
  alert("1dbtn clicked");
});

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

        alert("Phase difference computed and displayed!");
    } catch (error) {
        console.error("Error:", error);
        alert("Error: " + error.message);
    }
}


async function fetch3DPlot() {
    try {
        const response = await fetch("http://192.168.1.121:8000/compute_3d");
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        document.getElementById("output3D").innerHTML = `<span>3D</span>${data.html}`;
    } catch (error) {
        console.error("Error:", error);
        alert("Error: " + error.message);
    }
}


function startROISelection() {
    if (!phaseImage.src || phaseImage.src.length === 0) {
        alert("No phase difference image available.");
        return;
    }
    roiCanvas.width = phaseImage.width;
    roiCanvas.height = phaseImage.height;
    roiCanvas.style.width = phaseImage.width + "px";
    roiCanvas.style.height = phaseImage.height + "px";

    selectingROI = true;
    ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
    alert("Draw ROI on the image by clicking and dragging.");
}

roiCanvas.addEventListener("mousedown", (e) => {
    if (!selectingROI) return;
    const rect = roiCanvas.getBoundingClientRect();
    startX = e.clientX - rect.left;
    startY = e.clientY - rect.top;
});

roiCanvas.addEventListener("mousemove", (e) => {
    if (!selectingROI || startX === undefined) return;
    const rect = roiCanvas.getBoundingClientRect();
    const currentX = e.clientX - rect.left;
    const currentY = e.clientY - rect.top;
    const width = currentX - startX;
    const height = currentY - startY;

    ctx.clearRect(0, 0, roiCanvas.width, roiCanvas.height);
    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    ctx.strokeRect(startX, startY, width, height);
});

roiCanvas.addEventListener("mouseup", async (e) => {
    if (!selectingROI) return;
    const rect = roiCanvas.getBoundingClientRect();
    endX = e.clientX - rect.left;
    endY = e.clientY - rect.top;

    selectingROI = false;

    // Convert to proper coordinates (integers)
    const x1 = Math.round(Math.min(startX, endX));
    const y1 = Math.round(Math.min(startY, endY));
    const x2 = Math.round(Math.max(startX, endX));
    const y2 = Math.round(Math.max(startY, endY));

    // Send ROI to backend
    await selectROI(x1, y1, x2, y2);
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



document.getElementById('mainGallery').addEventListener('click', () => {
  const details = document.getElementById('outputImages');
  if (details.style.display === 'flex') {
    details.style.display = 'none';
  } else {
    details.style.display = 'flex';
  }
});