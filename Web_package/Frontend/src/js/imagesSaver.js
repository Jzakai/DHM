 const savedImages = [
    'image1.jpg',
    'image2.png',
    'photo3.jpeg'
  ];

  const loadBtn = document.getElementById('loadImage');
  const imageSelect = document.getElementById('image-status');

  loadBtn.addEventListener('click', () => {
    // Clear the current options
    imageSelect.innerHTML = '';

    if (savedImages.length === 0) {
      const option = document.createElement('option');
      option.value = '';
      option.disabled = true;
      option.selected = true;
      option.hidden = true;
      option.textContent = 'None Available';
      imageSelect.appendChild(option);
      return;
    }

    // Add a default "Select an image" option
    const defaultOption = document.createElement('option');
    defaultOption.value = '';
    defaultOption.disabled = true;
    defaultOption.selected = true;
    defaultOption.hidden = true;
    defaultOption.textContent = 'Select an image';
    imageSelect.appendChild(defaultOption);

    // Add saved images as options
    savedImages.forEach(imgName => {
      const option = document.createElement('option');
      option.value = imgName;
      option.textContent = imgName;
      imageSelect.appendChild(option);
    });
  });