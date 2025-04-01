<template>
  <div class="app-container">
    <header>
      <h1>找到地球的另一端</h1>
    </header>
    
    <main>
      <div class="location-input">
        <div class="input-group">
          <label for="location">输入位置或地标：</label>
          <input 
            type="text" 
            id="location" 
            v-model="locationInput" 
            placeholder="例如：北京, 中国" 
            @keyup.enter="searchLocation"
          />
          <button @click="searchLocation">搜索</button>
        </div>
        
        <div class="or-divider">或者</div>
        
        <button @click="useCurrentLocation" class="current-location-btn">
          使用我的当前位置
        </button>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
      </div>
      
      <div class="maps-container" v-if="showMaps">
        <div class="map-wrapper">
          <h2>当前位置</h2>
          <div id="originMap" class="map"></div>
          <div class="location-info" v-if="originInfo.length > 0">
            <h3>附近地点</h3>
            <div v-for="(place, index) in originInfo" :key="'origin-'+index" class="place-info">
              <h4>{{ place.title }}</h4>
              <p>{{ place.summary }}</p>
              <a :href="place.url" target="_blank">查看更多信息</a>
            </div>
          </div>
        </div>
        
        <div class="map-wrapper">
          <h2>对面位置</h2>
          <div id="antipodeMap" class="map"></div>
          <div class="location-info" v-if="antipodeInfo.length > 0">
            <h3>附近地点</h3>
            <div v-for="(place, index) in antipodeInfo" :key="'antipode-'+index" class="place-info">
              <h4>{{ place.title }}</h4>
              <p>{{ place.summary }}</p>
              <a :href="place.url" target="_blank">查看更多信息</a>
            </div>
          </div>
          <div v-else class="no-info">
            <p>这个位置可能是海洋或者人烟稀少的地区，没有找到相关信息</p>
          </div>
        </div>
      </div>
    </main>
    
    <footer>
      <p>© {{ new Date().getFullYear() }} 找到地球的另一端</p>
    </footer>
  </div>
</template>

<script>
import axios from 'axios';
import L from 'leaflet';

export default {
  name: 'App',
  data() {
    return {
      locationInput: '',
      originMap: null,
      antipodeMap: null,
      originMarker: null,
      antipodeMarker: null,
      originInfo: [],
      antipodeInfo: [],
      error: null,
      showMaps: false,
      currentCoords: {
        lat: null,
        lon: null,
      },
      antipodeCoords: {
        lat: null,
        lon: null,
      }
    };
  },
  mounted() {
    // 创建地图但不显示，直到用户输入位置
    this.initMaps();
  },
  methods: {
    initMaps() {
      // 初始化地图但不显示
      this.originMap = L.map('originMap', {
        center: [0, 0],
        zoom: 2
      });
      
      this.antipodeMap = L.map('antipodeMap', {
        center: [0, 0],
        zoom: 2
      });
      
      // 添加地图图层
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(this.originMap);
      
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
      }).addTo(this.antipodeMap);
    },
    
    useCurrentLocation() {
      if (navigator.geolocation) {
        this.error = null;
        navigator.geolocation.getCurrentPosition(
          position => {
            this.currentCoords.lat = position.coords.latitude;
            this.currentCoords.lon = position.coords.longitude;
            this.getAntipodeInfo(this.currentCoords.lat, this.currentCoords.lon);
          },
          error => {
            this.error = `无法获取您的位置: ${error.message}`;
          }
        );
      } else {
        this.error = "您的浏览器不支持地理位置功能";
      }
    },
    
    searchLocation() {
      if (!this.locationInput.trim()) {
        this.error = "请输入位置";
        return;
      }
      
      this.error = null;
      
      // 使用OpenStreetMap Nominatim服务进行地理编码
      axios.get(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(this.locationInput)}`)
        .then(response => {
          if (response.data && response.data.length > 0) {
            const location = response.data[0];
            this.currentCoords.lat = parseFloat(location.lat);
            this.currentCoords.lon = parseFloat(location.lon);
            this.getAntipodeInfo(this.currentCoords.lat, this.currentCoords.lon);
          } else {
            this.error = "找不到该位置，请尝试更具体的地点";
          }
        })
        .catch(error => {
          this.error = `搜索位置时出错: ${error.message}`;
        });
    },
    
    getAntipodeInfo(lat, lon) {
      // 向后端API请求对面位置信息
      axios.get(`http://localhost:5000/api/antipode?lat=${lat}&lon=${lon}`)
        .then(response => {
          const data = response.data;
          
          // 更新对面位置的坐标
          this.antipodeCoords.lat = data.antipode.lat;
          this.antipodeCoords.lon = data.antipode.lon;
          
          // 更新信息
          this.originInfo = data.origin.info;
          this.antipodeInfo = data.antipode.info;
          
          // 显示地图
          this.showMaps = true;
          
          // 需要等待DOM更新后再更新地图
          this.$nextTick(() => {
            this.updateMaps();
          });
        })
        .catch(error => {
          this.error = `获取对面位置信息时出错: ${error.message}`;
        });
    },
    
    updateMaps() {
      // 更新原始位置地图
      this.originMap.setView([this.currentCoords.lat, this.currentCoords.lon], 10);
      
      // 更新对面位置地图
      this.antipodeMap.setView([this.antipodeCoords.lat, this.antipodeCoords.lon], 10);
      
      // 清除已有标记
      if (this.originMarker) {
        this.originMap.removeLayer(this.originMarker);
      }
      
      if (this.antipodeMarker) {
        this.antipodeMap.removeLayer(this.antipodeMarker);
      }
      
      // 添加新标记
      this.originMarker = L.marker([this.currentCoords.lat, this.currentCoords.lon])
        .addTo(this.originMap)
        .bindPopup("您的位置")
        .openPopup();
      
      this.antipodeMarker = L.marker([this.antipodeCoords.lat, this.antipodeCoords.lon])
        .addTo(this.antipodeMap)
        .bindPopup("对面的位置")
        .openPopup();
      
      // 刷新地图大小以确保正确显示
      this.originMap.invalidateSize();
      this.antipodeMap.invalidateSize();
    }
  }
};
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Arial', sans-serif;
  line-height: 1.6;
  color: #333;
  background-color: #f4f4f4;
}

.app-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

header {
  text-align: center;
  margin-bottom: 30px;
}

header h1 {
  color: #2c3e50;
  font-size: 2.5rem;
}

.location-input {
  max-width: 600px;
  margin: 0 auto 40px;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.input-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 15px;
}

.input-group label {
  margin-bottom: 5px;
  font-weight: bold;
}

.input-group input {
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 16px;
  margin-bottom: 10px;
}

button {
  padding: 10px 15px;
  background-color: #3498db;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background-color 0.3s;
}

button:hover {
  background-color: #2980b9;
}

.or-divider {
  text-align: center;
  margin: 15px 0;
  color: #666;
}

.current-location-btn {
  width: 100%;
  padding: 12px;
  background-color: #2ecc71;
}

.current-location-btn:hover {
  background-color: #27ae60;
}

.error-message {
  color: #e74c3c;
  margin-top: 15px;
  padding: 10px;
  background-color: #fadbd8;
  border-radius: 4px;
}

.maps-container {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 40px;
}

.map-wrapper {
  flex: 1;
  min-width: 300px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  padding: 20px;
}

.map-wrapper h2 {
  margin-bottom: 15px;
  color: #2c3e50;
}

.map {
  height: 400px;
  border-radius: 4px;
  margin-bottom: 20px;
}

.location-info {
  margin-top: 20px;
}

.location-info h3 {
  margin-bottom: 15px;
  color: #2c3e50;
}

.place-info {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.place-info h4 {
  color: #3498db;
  margin-bottom: 10px;
}

.place-info p {
  margin-bottom: 10px;
  color: #666;
}

.place-info a {
  color: #3498db;
  text-decoration: none;
}

.place-info a:hover {
  text-decoration: underline;
}

.no-info {
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 4px;
  color: #666;
  text-align: center;
}

footer {
  text-align: center;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eee;
  color: #666;
}

@media (max-width: 768px) {
  .maps-container {
    flex-direction: column;
  }
  
  .map-wrapper {
    min-width: 100%;
  }
}
</style>









