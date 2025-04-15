const authApiUrl = 'https://your-domain.com/api/auth';

async function checkAuthAndRedirect() {
    const currentPath = window.location.pathname;
    console.log('현재 경로:', currentPath);

    try {
        const response = await fetch(authApiUrl, {
            method: 'GET',
            credentials: 'include'
        });

        if (response.ok) {
            console.log('인증 성공');

            if (currentPath === '/') {
                console.log('메인으로 이동');
                window.location.href = '/pages/main';
                return;
            }

            // 인증 성공 시 화면 보여주기
            document.body.classList.remove('hidden');

        } else {
            console.log('인증 실패 - 로그인 페이지로 이동');
            if (currentPath !== '/') {
                window.location.replace('/');
            } else {
                document.body.classList.remove('hidden'); // 로그인 페이지는 예외적으로 보여줌
            }
        }
    } catch (error) {
        console.error('서버 인증 확인 중 오류:', error);
        if (currentPath !== '/') {
            window.location.replace('/');
        } else {
            document.body.classList.remove('hidden');
        }
    }
}

document.addEventListener('DOMContentLoaded', checkAuthAndRedirect);
