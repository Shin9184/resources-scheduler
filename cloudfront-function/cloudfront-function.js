// CloudFront Function 핸들러: URL 경로를 자동으로 처리하는 함수
function handler(event) {
    var request = event.request;   // CloudFront가 수신한 요청 객체
    var uri = request.uri;         // 요청된 URI 경로 (예: /pages/main)

    // 정적 리소스(js, css, 이미지 등)는 변경 없이 그대로 통과
    if (uri.match(/\.(js|css|png|jpg|jpeg|svg)$/)) {
        return request;  // .html 처리하지 않음
    }

    // 루트 경로('/')나 이미 .html로 끝나는 경우는 처리하지 않고 그대로 반환
    if (uri === '/' || uri.endsWith('.html')) {
        return request;
    }

    // /pages/ 경로에 대한 자동 HTML 확장자 추가 처리
    if (uri.startsWith('/pages/')) {
        if (!uri.endsWith('/')) {
            // 슬래시로 끝나지 않는 경우: /pages/main → /pages/main.html
            request.uri = uri + '.html';
        } else {
            // 슬래시로 끝나는 경우: /pages/main/ → /pages/main.html (마지막 / 제거)
            request.uri = uri.slice(0, -1) + '.html';
        }
    }

    // 최종적으로 변경되거나 그대로인 URI를 포함한 요청 객체 반환
    return request;
}