new Vue({
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
            activeForm: 'login', // 默认显示登录表单
            
            // 登录表单
            loginForm: {
                username: '',
                password: ''
            },
            
            // 注册表单
            registerForm: {
                username: '',
                password: '',
                confirmPassword: '',
                email: '',
                phone: ''
            },
            
            // 表单验证规则
            loginRules: {
                username: [
                    { required: true, message: '请输入用户名或邮箱', trigger: 'blur' }
                ],
                password: [
                    { required: true, message: '请输入密码', trigger: 'blur' },
                    { min: 8, message: '密码长度至少为8个字符', trigger: 'blur' }
                ]
            },
            
            registerRules: {
                username: [
                    { required: true, message: '请输入用户名', trigger: 'blur' },
                    { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
                ],
                password: [
                    { required: true, message: '请输入密码', trigger: 'blur' },
                    { min: 8, message: '密码长度至少为8个字符', trigger: 'blur' },
                    { pattern: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$/, message: '密码必须包含字母和数字', trigger: 'blur' }
                ],
                confirmPassword: [
                    { required: true, message: '请再次输入密码', trigger: 'blur' },
                    { validator: validatePass, trigger: 'blur' }
                ],
                email: [
                    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
                    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
                ],
                phone: [
                    { pattern: /^1\d{10}$/, message: '请输入正确的手机号码', trigger: 'blur' }
                ]
            },
            
            // 表单提交状态
            loading: false
        };
    },
    
    methods: {
        // 切换表单
        switchForm(formName) {
            this.activeForm = formName;
        },
        
        // 提交表单
        submitForm(formName) {
            this.$refs[formName].validate((valid) => {
                if (valid) {
                    if (formName === 'loginForm') {
                        this.login();
                    } else if (formName === 'registerForm') {
                        this.register();
                    }
                } else {
                    console.log('表单验证失败');
                    return false;
                }
            });
        },
        
        // 登录方法
        login() {
            this.loading = true;
            
            axios.post('/accounts/login/', {
                username: this.loginForm.username,
                password: this.loginForm.password
            })
            .then(response => {
                this.loading = false;
                if (response.data.status === 'success') {
                    this.$message.success('登录成功');
                    
                    // 保存用户信息和JWT令牌
                    const userData = response.data.data;
                    localStorage.setItem('user', JSON.stringify({
                        username: userData.username,
                        email: userData.email
                    }));
                    localStorage.setItem('token', userData.token);
                    
                    // 设置axios默认请求头，添加授权信息
                    axios.defaults.headers.common['Authorization'] = `Bearer ${userData.token}`;
                    
                    // 重定向到首页
                    setTimeout(() => {
                        window.location.href = '/accounts/';
                    }, 1000);
                } else {
                    this.$message.error(response.data.message || '登录失败');
                }
            })
            .catch(error => {
                this.loading = false;
                if (error.response) {
                    this.$message.error(error.response.data.message || '登录失败');
                } else {
                    this.$message.error('网络错误，请稍后重试');
                }
            });
        },
        
        // 注册方法
        register() {
            this.loading = true;
            
            // 构造提交的数据对象
            const postData = {
                username: this.registerForm.username,
                password: this.registerForm.password,
                email: this.registerForm.email
            };
            
            // 如果有手机号，则添加
            if (this.registerForm.phone) {
                postData.phone = this.registerForm.phone;
            }
            
            axios.post('/accounts/register/', postData)
            .then(response => {
                this.loading = false;
                if (response.data.status === 'success') {
                    this.$message.success('注册成功');
                    // 切换到登录表单
                    this.switchForm('login');
                    // 自动填入刚注册的用户名
                    this.loginForm.username = this.registerForm.username;
                } else {
                    this.$message.error(response.data.message || '注册失败');
                }
            })
            .catch(error => {
                this.loading = false;
                if (error.response) {
                    this.$message.error(error.response.data.message || '注册失败');
                } else {
                    this.$message.error('网络错误，请稍后重试');
                }
            });
        }
    },
    
    // 在组件创建时检查是否已登录
    created() {
        // 检查本地存储中是否有令牌
        const token = localStorage.getItem('token');
        if (token) {
            // 设置axios默认请求头，添加授权信息
            axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
            
            // 已登录状态下直接跳转到首页
            window.location.href = '/accounts/';
        }
    }
}); 