// Chỉ đặt URL công khai của FastAPI tại đây.
window.YTEMO_CONFIG = {
  apiBase: ["localhost", "127.0.0.1", ""].includes(location.hostname)
    ? "http://127.0.0.1:8000"
    : location.origin,
  homePhoto: "assets/images/trang-chu.jpg",
  communityPhoto: "assets/images/cong-dong.jpg"
};
