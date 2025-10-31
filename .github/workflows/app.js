class TelegramMiniApp {
    constructor() {
        this.tg = window.Telegram.WebApp;
        this.apiBaseUrl = ' t.me/Istoriyaa_bot'; // URL вашего бота
        this.init();
    }

    init() {
        this.tg.expand();
        this.tg.enableClosingConfirmation();
        this.loadUserData();
        this.setupEventListeners();
    }

    async loadUserData() {
        const user = this.tg.initDataUnsafe.user;
        if (user) {
            try {
                const response = await fetch(`${this.apiBaseUrl}/user/${user.id}`);
                const data = await response.json();
                this.renderUserData(data);
            } catch (error) {
                console.error('Error loading user data:', error);
            }
        }
    }

    renderUserData(data) {
        document.getElementById('userInfo').innerHTML = `
            <div class="user-card">
                <h3>Привет, ${data.first_name}! 👋</h3>
                <p>Призов получено: ${data.prizes_count}</p>
            </div>
        `;
    }

    async playGame() {
        try {
            const user = this.tg.initDataUnsafe.user;
            const response = await fetch(`${this.apiBaseUrl}/play`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: user.id
                })
            });
            
            const result = await response.json();
            this.showPrize(result.prize);
            
        } catch (error) {
            console.error('Error playing game:', error);
        }
    }

    showPrize(prize) {
        document.getElementById('prizeResult').innerHTML = `
            <div class="prize-card">
                <h2>🎉 Поздравляем!</h2>
                <p>Вы выиграли: <strong>${prize.name}</strong></p>
                <p>Действует: ${prize.duration_hours} часов</p>
            </div>
        `;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.app = new TelegramMiniApp();
});
