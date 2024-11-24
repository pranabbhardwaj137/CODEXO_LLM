const uploadForm = document.getElementById('uploadForm');
const loadingBarContainer = document.getElementById('loadingBarContainer');
const loadingBar = document.getElementById('loadingBar');
const resultDiv = document.getElementById('result');

uploadForm.onsubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(uploadForm);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/upload", true);

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
            const percent = (event.loaded / event.total) * 100;
            loadingBarContainer.style.display = 'block';
            loadingBar.style.width = `${percent}%`;
            loadingBar.textContent = `${Math.round(percent)}%`;
        }
    };

    xhr.onload = () => {
        loadingBarContainer.style.display = 'none';
        if (xhr.status === 200) {
            const response = JSON.parse(xhr.responseText);
            resultDiv.innerHTML = `<p>${response.message}</p>`;
            const img = document.createElement("img");
            img.src = response.layout_image;
            img.id = "generatedImage";
            resultDiv.appendChild(img);
        } else {
            resultDiv.innerHTML = `<p>Error: ${xhr.responseText}</p>`;
        }
    };

    xhr.onerror = () => {
        loadingBarContainer.style.display = 'none';
        resultDiv.innerHTML = "<p>An error occurred. Please try again.</p>";
    };

    xhr.send(formData);
};
