// 认证页面Vue应用
window.app = new Vue({
    el: '#app',
    data() {
        // 自定义校验密码一致性
        const validatePass = (rule, value, callback) => {
            if (value === '') {
                callback(new Error('请再次输入密码'));
            } else if (value !== this.registerForm.password) {
                callback(new Error('两次输入密码不一致'));
            } else {
                callback();
            }
        };
        
        return {
            activeTab: 'login',
            loginForm: {
                username: '',
                password: '',
                captchaToken: ''  // Cloudflare Turnstile令牌
            },
            registerForm: {
                username: '',
                password: '',
                password2: '',
                email: '',
                phone: '',
                verification_code: '',
                captchaToken: ''  // Cloudflare Turnstile令牌
            },
            loading: false,
            countdown: 0,
            countdownTimer: null,
            isDevEnvironment: false // 将由服务器传递的变量设置
        };
    },
    computed: {
        // 注册表单验证
        canRegister() {
            return this.registerForm.username &&
                   this.registerForm.password &&
                   this.registerForm.password === this.registerForm.password2 &&
                   this.registerForm.email &&
                   this.registerForm.verification_code;
        },
        // 是否可以发送验证码
        canSendCode() {
            return this.registerForm.email && !this.countdown;
        }
    },
    mounted() {
        // 在非开发环境中，渲染Turnstile组件
        this.$nextTick(() => {
            setTimeout(() => {
                this.renderTurnstile();
            }, 500);
        });
    },
    created() {
        // 检查是否已登录
        const token = localStorage.getItem('token');
        if (token) {
            window.location.href = '/accounts/';
        }
    },
    methods: {
        // 渲染Turnstile组件
        renderTurnstile() {
            if (typeof turnstile !== 'undefined' && window.ENV && window.ENV.turnstileSiteKey) {
                console.log('渲染Turnstile组件，密钥:', window.ENV.turnstileSiteKey);
                
                // 渲染登录验证
                if (document.getElementById('login-turnstile')) {
                    turnstile.render('#login-turnstile', {
                        sitekey: window.ENV.turnstileSiteKey,
                        callback: (token) => {
                            console.log('登录验证成功');
                            this.loginForm.captchaToken = token;
                        }
                    });
                }
                
                // 渲染注册验证
                if (document.getElementById('register-turnstile')) {
                    turnstile.render('#register-turnstile', {
                        sitekey: window.ENV.turnstileSiteKey,
                        callback: (token) => {
                            console.log('注册验证成功');
                            this.registerForm.captchaToken = token;
                        }
                    });
                }
            } else {
                console.error('Turnstile未加载或密钥未设置');
                // 3秒后重试
                setTimeout(() => {
                    this.renderTurnstile();
                }, 3000);
            }
        },
        
        // 登录方法
        login() {
            // 在生产环境中检查验证码
            if (!this.isDevEnvironment && !this.loginForm.captchaToken) {
                this.$message.warning('请完成人机验证');
                return;
            }

            this.loading = true;
            
            // 构建登录数据，包含人机验证令牌
            const loginData = {
                username: this.loginForm.username,
                password: this.loginForm.password,
                captcha_token: this.loginForm.captchaToken || 'dev_mode'
            };
            
            axios.post('/accounts/login/', loginData)
                .then(response => {
                    if (response.data.status === 'success') {
                        console.log('Login response:', response.data);
                        
                        // 保存用户信息和令牌
                        localStorage.setItem('token', response.data.token);
                        
                        // 确保用户信息包含is_staff属性和兴趣标签选择状态
                        const userInfo = {
                            username: response.data.username,
                            email: response.data.email,
                            is_staff: response.data.is_staff || false,
                            id: response.data.user_id,
                            interests_selected: response.data.interests_selected || false
                        };
                        
                        console.log('保存用户信息:', userInfo);
                        localStorage.setItem('user', JSON.stringify(userInfo));
                        
                        // 在cookie中也存储token (用于服务器端读取)
                        document.cookie = `token=${response.data.token}; path=/; max-age=604800`;
                        
                        // 设置默认请求头
                        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
                        
                        // 检查是否需要选择兴趣标签
                        if (!response.data.interests_selected) {
                            // 如果用户还没有选择兴趣标签，跳转到兴趣选择页面
                            window.location.href = '/accounts/interests/';
                        } else {
                            // 跳转到主页
                            window.location.href = '/accounts/';
                        }
                    } else {
                        this.$message.error(response.data.message);
                        // 重置验证码
                        this.resetCaptcha('login');
                    }
                })
                .catch(error => {
                    this.$message.error('登录失败，请稍后重试');
                    console.error(error);
                    // 重置验证码
                    this.resetCaptcha('login');
                })
                .finally(() => {
                    this.loading = false;
                });
        },
        
        // 注册方法
        register() {
            if (!this.canRegister) {
                this.$message.warning('请完成所有必填项');
                return;
            }
            
            // 在生产环境中检查验证码
            if (!this.isDevEnvironment && !this.registerForm.captchaToken) {
                this.$message.warning('请完成人机验证');
                return;
            }
            
            this.loading = true;
            
            // 构建注册数据，包含人机验证令牌
            const registerData = {
                username: this.registerForm.username,
                password: this.registerForm.password,
                password2: this.registerForm.password2,
                email: this.registerForm.email,
                phone: this.registerForm.phone,
                verification_code: this.registerForm.verification_code,
                captcha_token: this.registerForm.captchaToken || 'dev_mode'
            };
            
            axios.post('/accounts/register/', registerData)
                .then(response => {
                    if (response.data.status === 'success') {
                        this.$message.success(response.data.message);
                        
                        // 保存用户信息和令牌
                        localStorage.setItem('token', response.data.token);
                        localStorage.setItem('user', JSON.stringify({
                            username: response.data.username,
                            email: response.data.email,
                            interests_selected: false  // 新注册用户默认未选择兴趣标签
                        }));
                        
                        // 设置默认请求头
                        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.token}`;
                        
                        // 新注册用户需要选择兴趣标签
                        window.location.href = '/accounts/interests/';
                    } else {
                        this.$message.error(response.data.message);
                        // 重置验证码
                        this.resetCaptcha('register');
                    }
                })
                .catch(error => {
                    this.$message.error('注册失败，请稍后重试');
                    console.error(error);
                    // 重置验证码
                    this.resetCaptcha('register');
                })
                .finally(() => {
                    this.loading = false;
                });
        },
        
        // 发送验证码
        sendVerificationCode() {
            if (!this.registerForm.email) {
                this.$message.warning('请先填写邮箱');
                return;
            }
            
            this.loading = true;
            
            axios.post('/accounts/send-verification-code/', { email: this.registerForm.email })
                .then(response => {
                    if (response.data.status === 'success') {
                        this.$message.success(response.data.message);
                        this.startCountdown();
                    } else {
                        this.$message.error(response.data.message);
                    }
                })
                .catch(error => {
                    this.$message.error('发送验证码失败，请稍后重试');
                    console.error(error);
                })
                .finally(() => {
                    this.loading = false;
                });
        },
        
        // 开始倒计时
        startCountdown() {
            this.countdown = 60;
            this.countdownTimer = setInterval(() => {
                this.countdown -= 1;
                if (this.countdown <= 0) {
                    clearInterval(this.countdownTimer);
                }
            }, 1000);
        },
        
        // 切换标签页
        switchTab(tab) {
            this.activeTab = tab;
            // 重置验证码
            this.resetCaptcha('both');
            
            // 重新渲染Turnstile
            this.$nextTick(() => {
                this.renderTurnstile();
            });
        },
        
        // 重置Cloudflare Turnstile验证码
        resetCaptcha(type) {
            if (type === 'login' || type === 'both') {
                this.loginForm.captchaToken = '';
                if (typeof turnstile !== 'undefined') {
                    turnstile.reset('#login-turnstile');
                }
            }
            
            if (type === 'register' || type === 'both') {
                this.registerForm.captchaToken = '';
                if (typeof turnstile !== 'undefined') {
                    turnstile.reset('#register-turnstile');
                }
            }
        }
    }
}); 