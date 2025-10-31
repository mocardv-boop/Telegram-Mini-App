// Telegram Web App initialization
const tg = window.Telegram.WebApp;

// Initialize the app
tg.expand();
tg.enableClosingConfirmation();
tg.BackButton.onClick(() => {
    showMainScreen();
});
tg.BackButton.hide();

// User data
let userData = null;
let userPrizes = [];

// Initialize app
async function initApp() {
    // Get user data from Telegram
    const user = tg.initDataUnsafe.user;
    
    if (user) {
        document.getElementById('userInfo').innerHTML = `
            <div style="text-align: center; margin-bottom: 20px;">
                <p>Привет, <strong>${user.first_name}</strong>! 👋</p>
            </div>
        `;
        
        // Load user data from backend
        await loadUserData(user.id);
    } else {
        document.getElementById('userInfo').innerHTML = `
            <div style="text-align: center; margin-bottom: 20px;">
                <p>Добро пожаловать! 👋</p>
            </div>
        `;
    }
}

// Load user data from backend
async function loadUserData(userId) {
    try {
        const response = await fetch(`/api/user/${userId}`);
        const data = await response.json();
        
        userData = data;
        userPrizes = data.prizes || [];
        
        // Update UI
        document.getElementById('prizesCount').textContent = data.prizes_count || 0;
        document.getElementById('daysPlayed').textContent = data.days_played || 0;
        
    } catch (error) {
        console.error('Error loading user data:', error);
    }
}

// Play the game
async function playGame() {
    try {
        const response = await fetch('/api/play', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: tg.initDataUnsafe.user?.id
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showPrizeResult(result.prize);
            await loadUserData(tg.initDataUnsafe.user?.id);
        } else {
            alert(result.message || 'Произошла ошибка');
        }
        
    } catch (error) {
        console.error('Error playing game:', error);
        alert('Ошибка соединения');
    }
}

// Show prize result
function showPrizeResult(prize) {
    document.getElementById('prizeName').textContent = prize.name;
    document.getElementById('prizeDescription').textContent = 
        `Приз действует: ${prize.duration_hours} часов`;
    
    document.getElementById('prizeResult').style.display = 'block';
    document.getElementById('prizesList').style.display = 'none';
}

// Show user prizes
function showPrizes() {
    const container = document.getElementById('prizesContainer');
    container.innerHTML = '';
    
    if (userPrizes.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666;">У вас пока нет призов</p>';
    } else {
        userPrizes.forEach(prize => {
            const prizeElement = document.createElement('div');
            prizeElement.className = 'prize-item';
            prizeElement.style.cssText = `
                padding: 15px;
                margin: 10px 0;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #28a745;
            `;
            
            const status = prize.is_active ? '✅ Активен' : '❌ Неактивен';
            prizeElement.innerHTML = `
                <strong>${prize.name}</strong><br>
                <small>Получен: ${new Date(prize.won_date).toLocaleDateString()}</small><br>
                <small>${status}</small>
            `;
            
            container.appendChild(prizeElement);
        });
    }
    
    document.getElementById('prizesList').style.display = 'block';
    document.getElementById('prizeResult').style.display = 'none';
    tg.BackButton.show();
}

// Show user profile
function showProfile() {
    if (userData) {
        alert(`
Профиль пользователя:

Имя: ${userData.first_name} ${userData.last_name}
Username: @${userData.username}
Зарегистрирован: ${userData.registration_date}
Получено призов: ${userData.prizes_count}
        `);
    }
}

// Show main screen
function showMainScreen() {
    document.getElementById('prizesList').style.display = 'none';
    document.getElementById('prizeResult').style.display = 'none';
    tg.BackButton.hide();
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initApp);