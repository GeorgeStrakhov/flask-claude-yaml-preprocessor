document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('processorForm');
    const submitBtn = document.getElementById('submitBtn');
    const spinner = submitBtn.querySelector('.spinner-border');
    const resultPre = document.getElementById('result');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Show loading state
        submitBtn.disabled = true;
        spinner.classList.remove('d-none');
        resultPre.textContent = 'Processing...';
        
        try {
            const formData = new FormData(form);
            
            const response = await fetch('/process', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok) {
                resultPre.textContent = data.result;
            } else {
                resultPre.textContent = `Error: ${data.error}`;
            }
        } catch (error) {
            resultPre.textContent = `Error: ${error.message}`;
        } finally {
            // Reset loading state
            submitBtn.disabled = false;
            spinner.classList.add('d-none');
        }
    });
});
