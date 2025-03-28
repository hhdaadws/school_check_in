// 首页Vue应用
new Vue({
    el: '#app',
    data() {
        return {
            isLoggedIn: false,
            userInfo: {},
            loading: true
        };
    },
    computed: {
        avatarInitial() {
            return this.userInfo.username ? this.userInfo.username[0].toUpperCase() : '?';
        },
        displayUsername() {
            return this.userInfo.username || '未设置';
        },
        displayEmail() {
            return this.userInfo.email || '未设置';
        }
    },
    created() {
        this.checkLoginStatus();
    },
    methods: {
        checkLoginStatus() {
            const token = localStorage.getItem('token');
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            
            if (token && user.username) {
                this.isLoggedIn = true;
                this.userInfo = user;
                axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
                this.getUserProfile();
            } else {
                this.loading = false;
            }
        },
        getUserProfile() {
            this.loading = true;
            
            axios.get('/accounts/profile/')
                .then(response => {
                    if (response.data.status === 'success') {
                        this.userInfo = response.data.data;
                        // 更新本地存储的用户信息
                        localStorage.setItem('user', JSON.stringify(response.data.data));
                    } else {
                        this.$message.error('获取用户资料失败');
                    }
                })
                .catch(error => {
                    if (error.response && error.response.status === 401) {
                        this.logout();
                    } else {
                        this.$message.error('获取用户资料失败');
                    }
                })
                .finally(() => {
                    this.loading = false;
                });
        },
        goToProfile() {
            // 跳转到个人资料页
            // 这里只是简单示例，实际可能需要单独的个人资料页面
            this.$message.info('已在当前页面显示个人资料');
        },
        goToLogin() {
            // 跳转到登录页
            window.location.href = '/accounts/auth/';
        },
        logout() {
            // 清除本地存储的用户信息和令牌
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            
            // 清除请求头中的授权信息
            delete axios.defaults.headers.common['Authorization'];
            
            // 更新状态
            this.isLoggedIn = false;
            this.userInfo = {};
            
            // 提示用户
            this.$message.success('已退出登录');
        }
    }
}); 