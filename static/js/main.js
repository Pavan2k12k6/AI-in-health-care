document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips with enhanced styling
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl, {
            template: '<div class="tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner shadow-sm"></div></div>',
            animation: true
        });
    });
    

    
    // Initialize Spline for modern 3D elements
    initializeSplineElements();
    
    // Add modern interaction effects
    addInteractionEffects();
    
    // Setup search functionality for patients list with enhanced animation
    const patientSearch = document.getElementById('patientSearch');
    if (patientSearch) {
        patientSearch.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const patientCards = document.querySelectorAll('.patient-card');
            
            patientCards.forEach(card => {
                const patientName = card.querySelector('.card-title').textContent.toLowerCase();
                const patientId = card.querySelector('.patient-id').textContent.toLowerCase();
                
                if (patientName.includes(searchTerm) || patientId.includes(searchTerm)) {
                    card.style.display = '';
                    card.style.opacity = '0';
                    setTimeout(() => {
                        card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 50);
                } else {
                    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        card.style.display = 'none';
                    }, 300);
                }
            });
        });
    }
    
    // Setup filter functionality for prescriptions with visual feedback
    const prescriptionFilter = document.getElementById('prescriptionFilter');
    if (prescriptionFilter) {
        prescriptionFilter.addEventListener('change', function() {
            const filterValue = this.value.toLowerCase();
            const prescriptionRows = document.querySelectorAll('#prescriptionsTable tbody tr');
            
            // Add a visual cue for which filter is active
            this.className = 'form-select';
            if (filterValue === 'pending') {
                this.classList.add('border-warning');
            } else if (filterValue === 'approved') {
                this.classList.add('border-success');
            } else if (filterValue === 'rejected') {
                this.classList.add('border-danger');
            }
            
            prescriptionRows.forEach((row, index) => {
                const status = row.querySelector('.prescription-status').textContent.toLowerCase();
                
                if (filterValue === 'all' || status === filterValue) {
                    row.style.display = '';
                    row.style.opacity = '0';
                    setTimeout(() => {
                        row.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
                        row.style.opacity = '1';
                        row.style.transform = 'translateX(0)';
                    }, index * 50); // Staggered animation
                } else {
                    row.style.transition = 'opacity 0.3s ease-in-out, transform 0.3s ease-in-out';
                    row.style.opacity = '0';
                    row.style.transform = 'translateX(20px)';
                    setTimeout(() => {
                        row.style.display = 'none';
                    }, 300);
                }
            });
        });
    }
    
    // Setup modern confirmation dialogs for critical actions
    const confirmActionButtons = document.querySelectorAll('.confirm-action');
    confirmActionButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const confirmMessage = this.getAttribute('data-confirm-message') || 'Are you sure you want to perform this action?';
            const actionUrl = this.href || this.form?.action;
            
            // Create and show a Bootstrap modal instead of browser confirm
            showConfirmationModal(confirmMessage, () => {
                if (this.tagName === 'A') {
                    window.location.href = actionUrl;
                } else if (this.form) {
                    this.form.submit();
                }
            });
        });
    });
    
    // Toggle medication status with modern confirmation
    const toggleMedicationForms = document.querySelectorAll('.toggle-medication-form');
    toggleMedicationForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const medicationName = this.getAttribute('data-medication-name');
            const currentStatus = this.getAttribute('data-current-status');
            const newStatus = currentStatus === 'active' ? 'deactivate' : 'activate';
            
            showConfirmationModal(`Are you sure you want to ${newStatus} ${medicationName}?`, () => {
                this.submit();
            });
        });
    });
    
    // Auto-populate drug name from RxNav suggestion with enhanced UI
    const medicationNameInput = document.getElementById('medication_name');
    const suggestionsList = document.getElementById('drug-suggestions');
    
    if (medicationNameInput && suggestionsList) {
        // Add modern styling to suggestions
        suggestionsList.classList.add('shadow-smooth', 'rounded-xl');
        
        // Add loading indicator
        const loadingIndicator = document.createElement('div');
        loadingIndicator.className = 'suggestion-loading text-center p-2 d-none';
        loadingIndicator.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Searching medications...';
        suggestionsList.parentNode.insertBefore(loadingIndicator, suggestionsList.nextSibling);
        
        // Debounce the input handler for better performance
        let debounceTimer;
        
        medicationNameInput.addEventListener('input', function() {
            const drugName = this.value.trim();
            
            if (drugName.length < 3) {
                suggestionsList.innerHTML = '';
                suggestionsList.style.display = 'none';
                loadingIndicator.classList.add('d-none');
                return;
            }
            
            // Show loading indicator
            loadingIndicator.classList.remove('d-none');
            
            // Clear previous timer
            clearTimeout(debounceTimer);
            
            // Set new timer
            debounceTimer = setTimeout(async function() {
                try {
                    // Use RxNav API to get drug name suggestions
                    const response = await fetch(`https://rxnav.nlm.nih.gov/REST/drugs.json?name=${encodeURIComponent(drugName)}`);
                    const data = await response.json();
                    
                    suggestionsList.innerHTML = '';
                    
                    if (data.drugGroup && data.drugGroup.conceptGroup) {
                        const conceptGroups = data.drugGroup.conceptGroup.filter(group => group.conceptProperties);
                        
                        if (conceptGroups.length > 0) {
                            // Get all drug names from the concept groups
                            const allDrugs = [];
                            
                            conceptGroups.forEach(group => {
                                group.conceptProperties.forEach(prop => {
                                    if (prop.name) {
                                        allDrugs.push({
                                            name: prop.name,
                                            rxcui: prop.rxcui
                                        });
                                    }
                                });
                            });
                            
                            // Display unique drug names (up to 10)
                            const uniqueDrugs = Array.from(new Map(allDrugs.map(drug => 
                                [drug.name, drug])).values()).slice(0, 10);
                            
                            if (uniqueDrugs.length > 0) {
                                suggestionsList.style.display = 'block';
                                
                                uniqueDrugs.forEach((drug, index) => {
                                    const item = document.createElement('div');
                                    item.classList.add('suggestion-item', 'p-2', 'border-bottom');
                                    
                                    // Add highlight for the matching part of the name
                                    const regex = new RegExp(`(${drugName})`, 'gi');
                                    const highlightedName = drug.name.replace(regex, '<strong>$1</strong>');
                                    
                                    item.innerHTML = `
                                        <div class="d-flex align-items-center">
                                            <i class="fas fa-pills me-2 text-primary"></i>
                                            <div>
                                                <div>${highlightedName}</div>
                                                <small class="text-muted">RxCUI: ${drug.rxcui}</small>
                                            </div>
                                        </div>
                                    `;
                                    
                                    // Add animation delay based on index
                                    item.style.animationDelay = `${index * 50}ms`;
                                    item.classList.add('fade-in');
                                    
                                    item.addEventListener('click', function() {
                                        medicationNameInput.value = drug.name;
                                        
                                        // Add rxcui to a hidden field if it exists
                                        const rxcuiInput = document.getElementById('rxcui');
                                        if (rxcuiInput) {
                                            rxcuiInput.value = drug.rxcui;
                                        }
                                        
                                        suggestionsList.style.display = 'none';
                                    });
                                    
                                    suggestionsList.appendChild(item);
                                });
                            } else {
                                showNoSuggestionsMessage();
                            }
                        } else {
                            showNoSuggestionsMessage();
                        }
                    } else {
                        showNoSuggestionsMessage();
                    }
                    
                    // Hide loading indicator
                    loadingIndicator.classList.add('d-none');
                    
                } catch (error) {
                    console.error('Error fetching drug suggestions:', error);
                    suggestionsList.style.display = 'none';
                    loadingIndicator.classList.add('d-none');
                }
            }, 300); // 300ms debounce
        });
        
        function showNoSuggestionsMessage() {
            suggestionsList.innerHTML = '';
            suggestionsList.style.display = 'block';
            
            const noResults = document.createElement('div');
            noResults.classList.add('p-3', 'text-center', 'text-muted');
            noResults.innerHTML = 'No medications found matching your search';
            suggestionsList.appendChild(noResults);
        }
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', function(e) {
            if (e.target !== medicationNameInput && !suggestionsList.contains(e.target)) {
                suggestionsList.style.display = 'none';
                loadingIndicator.classList.add('d-none');
            }
        });
    }
});

/**
 * Initialize Spline 3D elements on the page
 */
function initializeSplineElements() {
    // Load Spline config if available
    const splineScript = document.createElement('script');
    splineScript.src = '/static/js/spline/spline-config.js';
    splineScript.type = 'text/javascript';
    document.head.appendChild(splineScript);
    
    // Add Spline container to dashboard if appropriate page
    if (document.querySelector('.dashboard-overview')) {
        const dashboardHeader = document.querySelector('.dashboard-header');
        if (dashboardHeader) {
            const splineContainer = document.createElement('div');
            splineContainer.className = 'spline-container mb-4';
            splineContainer.setAttribute('data-scene-type', 'dashboard');
            splineContainer.setAttribute('data-height', '300px');
            
            dashboardHeader.parentNode.insertBefore(splineContainer, dashboardHeader);
        }
    }
    
    // Add Spline container to patient profile if appropriate page
    if (document.querySelector('.patient-info')) {
        const patientHeader = document.querySelector('.patient-info-header');
        if (patientHeader) {
            const splineContainer = document.createElement('div');
            splineContainer.className = 'spline-container mb-4';
            splineContainer.setAttribute('data-scene-type', 'patient');
            splineContainer.setAttribute('data-height', '250px');
            
            const parentElement = patientHeader.parentNode;
            parentElement.insertBefore(splineContainer, parentElement.firstChild);
        }
    }
    
    // Add DNA visualization to genotype pages
    if (document.querySelector('.genotype-analysis')) {
        const analysisHeader = document.querySelector('.genotype-analysis h2');
        if (analysisHeader) {
            const splineContainer = document.createElement('div');
            splineContainer.className = 'spline-container mb-4';
            splineContainer.setAttribute('data-scene-type', 'dna');
            splineContainer.setAttribute('data-height', '300px');
            
            analysisHeader.parentNode.insertBefore(splineContainer, analysisHeader.nextSibling);
        }
    }
}

/**
 * Add modern interaction effects to UI elements
 */
function addInteractionEffects() {
    // Add hover effects to cards
    document.querySelectorAll('.card').forEach(card => {
        card.classList.add('modern-card');
    });
    
    // Convert primary buttons to modern style
    document.querySelectorAll('.btn-primary').forEach(btn => {
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-modern-primary');
    });
    
    // Convert secondary buttons to modern style
    document.querySelectorAll('.btn-secondary').forEach(btn => {
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-modern-secondary');
    });
    
    // Add pulse animation to important action buttons
    document.querySelectorAll('.btn-danger, .btn-success').forEach(btn => {
        btn.classList.add('pulse');
    });
    
    // Enhance tables with modern styling
    document.querySelectorAll('table').forEach(table => {
        table.classList.add('border-0');
        
        // Add better styling to table headers
        const headers = table.querySelectorAll('th');
        headers.forEach(header => {
            header.style.borderTop = 'none';
            header.style.textTransform = 'uppercase';
            header.style.fontSize = '0.85rem';
            header.style.letterSpacing = '0.5px';
        });
    });
}

/**
 * Show a modern confirmation modal
 * @param {string} message - The confirmation message to display
 * @param {function} onConfirm - Callback to execute when confirmed
 */
function showConfirmationModal(message, onConfirm) {
    // Remove any existing confirmation modal
    const existingModal = document.getElementById('confirmationModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Create modal elements
    const modalDiv = document.createElement('div');
    modalDiv.className = 'modal fade';
    modalDiv.id = 'confirmationModal';
    modalDiv.setAttribute('tabindex', '-1');
    modalDiv.setAttribute('aria-labelledby', 'confirmationModalLabel');
    modalDiv.setAttribute('aria-hidden', 'true');
    
    modalDiv.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content rounded-xl shadow-smooth">
                <div class="modal-header">
                    <h5 class="modal-title" id="confirmationModalLabel">Confirm Action</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <div class="d-flex align-items-center mb-3">
                        <div class="me-3">
                            <i class="fas fa-exclamation-circle text-warning fa-2x"></i>
                        </div>
                        <div>
                            ${message}
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-modern-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-modern-primary" id="confirmActionBtn">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to document
    document.body.appendChild(modalDiv);
    
    // Initialize the Bootstrap modal
    const modalElement = document.getElementById('confirmationModal');
    const modal = new bootstrap.Modal(modalElement);
    
    // Add event listener to confirm button
    const confirmBtn = document.getElementById('confirmActionBtn');
    confirmBtn.addEventListener('click', function() {
        modal.hide();
        onConfirm();
    });
    
    // Show the modal
    modal.show();
    
    // Clean up modal when hidden
    modalElement.addEventListener('hidden.bs.modal', function() {
        modalElement.remove();
    });
}
