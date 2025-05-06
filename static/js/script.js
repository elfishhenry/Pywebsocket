document.addEventListener('DOMContentLoaded', function() {
    // Handle image likes
    const likeButtons = document.querySelectorAll('.like-btn');
    
    likeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const likeContainer = this.closest('.likes');
            const imageId = likeContainer.dataset.imageId;
            const likeCount = this.querySelector('.like-count');
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            // Send AJAX request to like the image
            fetch(`/like/${imageId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update like count
                    likeCount.textContent = data.likes;
                    
                    // Add visual feedback
                    button.classList.remove('btn-outline-danger');
                    button.classList.add('btn-danger');
                    button.classList.add('liked');
                    
                    // Create and animate heart elements for a fun effect
                    for (let i = 0; i < 5; i++) {
                        const heart = document.createElement('div');
                        heart.className = 'floating-heart';
                        heart.innerHTML = '<i class="fas fa-heart"></i>';
                        heart.style.left = `${Math.random() * 100}%`;
                        heart.style.animationDuration = `${Math.random() * 2 + 1}s`;
                        likeContainer.appendChild(heart);
                        
                        // Remove heart after animation completes
                        setTimeout(() => {
                            heart.remove();
                        }, 3000);
                    }
                    
                    // Show a temporary tooltip or message
                    const toast = document.createElement('div');
                    toast.className = 'toast position-fixed bottom-0 end-0 m-3';
                    toast.setAttribute('role', 'alert');
                    toast.setAttribute('aria-live', 'assertive');
                    toast.setAttribute('aria-atomic', 'true');
                    toast.innerHTML = `
                        <div class="toast-header bg-danger text-white">
                            <i class="fas fa-heart me-2"></i>
                            <strong class="me-auto">ImageShare</strong>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                        </div>
                        <div class="toast-body">
                            ${data.message}
                        </div>
                    `;
                    document.body.appendChild(toast);
                    
                    const bsToast = new bootstrap.Toast(toast);
                    bsToast.show();
                    
                    // Remove toast after it's hidden
                    toast.addEventListener('hidden.bs.toast', function() {
                        toast.remove();
                    });
                } else {
                    // Show error message
                    alert(data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('An error occurred while processing your request.');
            });
        });
    });
    
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
});
