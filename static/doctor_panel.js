async function fetchJson(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error('API error');
    return res.json();
}

function formatStatus(status) {
    if (status === 'Normal yürüyüş' || status === 'Normal ✅' || status === 'Normal Yürüyüş ✅') {
        return `<span class="status-normal">${status}</span>`;
    }
    return `<span class="status-bad">${status}</span>`;
}

function actionLink(patientId) {
    return `
        <a class="link-btn" href="/patient/${patientId}/view">Detay</a>
        <a class="link-btn" href="/report/${patientId}" style="margin-left:8px;">📄 Rapor</a>
    `;
}

async function loadDashboard() {
    try {
        const data = await fetchJson('/dashboard');
        document.getElementById('dashboard').innerHTML = `
            <div class="card-grid">
                <div class="patient">
                    <h3>Toplam Hasta</h3>
                    <p>${data.patients}</p>
                </div>
                <div class="patient">
                    <h3>Toplam Analiz</h3>
                    <p>${data.analyses}</p>
                </div>
                <div class="patient">
                    <h3>Normal</h3>
                    <p>${data.normal}</p>
                </div>
                <div class="patient">
                    <h3>Anormal</h3>
                    <p>${data.abnormal}</p>
                </div>
            </div>
        `;
    } catch (err) {
        document.getElementById('dashboard').textContent = 'Dashboard yüklenemedi.';
    }
}

async function loadPatients() {
    try {
        const patients = await fetchJson('/patients');
        if (patients.length === 0) {
            document.getElementById('patients').textContent = 'Hasta bulunamadı.';
            return;
        }

        let html = '';
        patients.forEach(p => {
            const lastAnalysis = p.analyses.length ? p.analyses[p.analyses.length - 1] : null;
            html += `
                <div class="patient">
                    <h3>${p.name}</h3>
                    <p>Yaş: ${p.age}</p>
                    <p>Cinsiyet: ${p.gender}</p>
                    <p>Analiz sayısı: ${p.analyses.length}</p>
                    ${lastAnalysis ? `
                        <p>Son Durum: ${formatStatus(lastAnalysis.status)}</p>
                        <p>Son Hastalık Tahmini: ${lastAnalysis.disease}</p>
                        <p>Doktor Etiketi: ${lastAnalysis.doctor_label || 'Beklemede'}</p>
                        <p class="small">Son analiz zamanı: ${lastAnalysis.time}</p>
                    ` : '<p class="small">Henüz analiz yok.</p>'}
                    <p>${actionLink(p.id)}</p>
                </div>
            `;
        });
        document.getElementById('patients').innerHTML = html;
    } catch (err) {
        document.getElementById('patients').textContent = 'Hasta listesi yüklenemedi.';
    }
}

window.onload = () => {
    loadDashboard();
    loadPatients();
    setInterval(() => {
        loadDashboard();
        loadPatients();
    }, 5000);
};