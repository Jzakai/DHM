let image = {
    psi: null,
    roi: null
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


    document.getElementById("openCam").addEventListener("click", initializeCamera);


    document.getElementById("stopCam").addEventListener("click", () => {
        if (stream) {
            stream.getTracks().forEach(t => t.stop());
            video.srcObject = null;
            stream = null;
        }
    });

    document.getElementById("imageFile").addEventListener("change", () => console.log("Object image selected"));
    document.getElementById("refFile").addEventListener("change", () => console.log("Reference image selected"));
    document.getElementById("1dbtn").addEventListener("click", (e) => { e.preventDefault(); startPointsSelection() });

    document.getElementById("checkSpectrum").addEventListener("click", () => alert("Check Spectrum clicked"));
    document.getElementById("phaseDiff").addEventListener("click", (e) => { e.preventDefault(); sendParams(); });
    document.getElementById("selectRoiBtn").addEventListener("click", startROISelection);
    document.getElementById("3dbtn").addEventListener("click", fetch3DPlot);
    document.getElementById("runAll").addEventListener("click", () => alert("Run All sequence started"));
    document.getElementById("2dbtn").addEventListener("click", () => alert("2dbtn clicked"));
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
        phaseOutputBox.innerHTML = `<div id="plotImage" style="width:100%; height:100%;"></div>`;

        Plotly.newPlot('plotImage', [], {
            images: [{
                source: "data:image/png;base64," + data.phase_image,
                x: 0,
                y: 0,
                sizex: 1,
                sizey: 1,
                xref: "x",
                yref: "y",
                sizing: "stretch",
                layer: "below"
            }],
            xaxis: {
                showgrid: false,
                zeroline: false,
                visible: false,
                constrain: "domain",
                range: [0, 1],
                autorange: false,
                fixedrange: false
            },
            yaxis: {
                showgrid: false,
                zeroline: false,
                visible: false,
                scaleanchor: "x",
                range: [1, 0], // flipped axis
                autorange: false,
                fixedrange: false
            },
            margin: { l: 0, r: 0, t: 0, b: 0 }
        }, {
            responsive: true,
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: [],
            modeBarButtonsToAdd: [],
            scrollZoom: true
        });


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

//recieves information returned from backend after 3d computation
async function fetch3DPlot() {
    try {
        const response = await fetch("http://192.168.1.121:8000/compute_3d");
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }
        const output3D = document.getElementById("output3D");
        output3D.innerHTML = `<div id="plot3d" style="width:100%; height:100%;"></div>`;

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


//1d profile

function startPointsSelection() {
    if (!image.roi && !image.psi) {
        alert("Please compute the phase difference first.");
        return;
    }

    else if (image.roi != null)
        selectPoints(image.roi);

    else
        selectPoints(image.psi);

}

function selectPoints(psi) {
    if (!psi) {
        alert("No phase image avai  lable. Please run phase difference first.");
        return;
    }

    const popup = window.open('', 'ImagePopup', 'width=800,height=600');
    popup.document.write(`
    <html>
    <head>
      <title>Select Points</title>
      <style>
        body { margin: 0; }
        canvas { display: block; cursor: crosshair; }
        #pixel-tooltip {
          position: fixed;
          background: rgba(0,0,0,0.7);
          color: white;
          padding: 4px 8px;
          font-family: monospace;
          font-size: 12px;
          border-radius: 4px;
          pointer-events: none;
          z-index: 1000;
        }
      </style>
    </head>
    <body>
      <canvas id="canvas"></canvas>
      <div id="pixel-tooltip"></div>
      <script>
        const canvas = document.getElementById('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        img.src = "data:image/png;base64,${psi}";

        let points = [];

        img.onload = function() {
          canvas.width = img.width;
          canvas.height = img.height;
          ctx.drawImage(img, 0, 0);
        };

        canvas.addEventListener('click', function(event) {
          const rect = canvas.getBoundingClientRect();
          const x = event.clientX - rect.left;
          const y = event.clientY - rect.top;
          points.push({ x, y });

          ctx.beginPath();
          ctx.arc(x, y, 5, 0, 2 * Math.PI);
          ctx.fillStyle = 'red';
          ctx.fill();

          if (points.length === 2) {
            ctx.beginPath();
            ctx.moveTo(points[0].x, points[0].y);
            ctx.lineTo(points[1].x, points[1].y);
            ctx.strokeStyle = 'blue';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            window.opener.receivePoints(points[0], points[1]);
            setTimeout(() => window.close(), 1000);
          }
        });

        canvas.addEventListener('mousemove', function(event) {
          const rect = canvas.getBoundingClientRect();
          const x = Math.floor(event.clientX - rect.left);
          const y = Math.floor(event.clientY - rect.top);
          if (x >= 0 && x < canvas.width && y >= 0 && y < canvas.height) {
            const pixel = ctx.getImageData(x, y, 1, 1).data;
            const [r, g, b, a] = pixel;
            const tooltip = document.getElementById('pixel-tooltip');
            tooltip.textContent = \`(\${x}, \${y}): R=\${r} G=\${g} B=\${b} A=\${a}\`;
            tooltip.style.left = \`\${event.clientX + 10}px\`;
            tooltip.style.top = \`\${event.clientY + 10}px\`;
          }
        });

        canvas.addEventListener('mouseleave', () => {
          const tooltip = document.getElementById('pixel-tooltip');
          tooltip.textContent = '';
        });
      <\/script>
    </body>
    </html>
  `);
}


function receivePoints(p1, p2) {
    point1 = p1;
    point2 = p2;
    console.log('Selected points:', point1, point2);
    fetch1DPlot();  // Call after user selects points
}

async function fetch1DPlot() {
    if (!point1 || !point2) {
        alert("Please select two points on the image.");
        return;
    }

    const x1 = Math.round(point1.x);
    const y1 = Math.round(point1.y);
    const x2 = Math.round(point2.x);
    const y2 = Math.round(point2.y);

    try {
        const response = await fetch("http://192.168.1.121:8000/compute_1d", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ x1, y1, x2, y2 })
        });

        // recieve thickness and distance to plot
        const data = await response.json();
        if (data.error) {
            alert(data.error);
            return;
        }

        const output1D = document.getElementById("output1D");

        // Ensure parent has height via CSS (see below)
        output1D.innerHTML = `
  <div id="plot1d" style="width:100%; height:100%;"></div>
`;

        // Create the plot
        Plotly.newPlot("plot1d", [{
            x: data.x,
            y: data.y,
            mode: 'lines',
            type: 'scatter',
            line: { color: 'blue' }
        }], {
            xaxis: { title: "Distance (μm)" },
            yaxis: { title: "Thickness (μm)" },
            margin: { l: 40, r: 10, b: 40, t: 10 }
        }, {
            responsive: true
        });

    } catch (error) {
        console.error("1D Error:", error);
        alert("Failed to generate 1D plot");
    }
}


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
            // Store the ROI image for display or selection
            image.roi = data.roi_image;

            // Optional: display the ROI image
            document.getElementById("roiOutput").innerHTML = `
              <img src="data:image/png;base64,${data.roi_image}" style="max-width:100%; border:1px solid #ccc;">
            `;

            alert("ROI selected and noise reduced!");
        }
    } catch (error) {
        console.error("Error selecting ROI:", error);
        alert("Error selecting ROI: " + error.message);
    }
}

const toggleBtn = document.getElementById('toggleBtn');
const slideDiv = document.getElementById('slideDiv');

toggleBtn.addEventListener('click', () => {
    slideDiv.classList.toggle('active');
});



document.getElementById('mainGallery').addEventListener('click', () => {
    const details = document.getElementById('outputImages');
    if (details.style.display === 'flex') {
        details.style.display = 'none';
    } else {
        details.style.display = 'flex';
    }
});


const rightPanel = document.querySelector('.right');

toggleCamera.addEventListener('click', () => {
    rightPanel.style.display = 'flex';
});

//camera
async function initializeCamera() {
    try {
        const res = await fetch("http://192.168.1.121:8000/start_camera");
        const data = await res.json();
        if (data.error) {
            alert("Failed to start camera: " + data.error);
        } else {
            document.getElementById("cameraStream").src = "http://192.168.1.121:8000/camera_feed";
        }
    } catch (err) {
        alert("Error connecting to server: " + err.message);
    }
}
