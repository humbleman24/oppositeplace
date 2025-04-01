<template>
  <div class="app-container">
    <header>
      <h1>找到地球的另一端</h1>
      <p class="instructions">左键拖动旋转地球，右键点击选择位置</p>
    </header>
    
    <main>
      <div class="globe-container">
        <div id="globe"></div>
        <div class="info-panel" v-if="showInfo">
          <div class="info-content">
            <h3>当前位置</h3>
            <p>纬度: {{ originCoords.lat.toFixed(2) }}°</p>
            <p>经度: {{ originCoords.lon.toFixed(2) }}°</p>
            <div v-if="originInfo.length > 0">
              <h4>附近地点</h4>
              <div v-for="(place, index) in originInfo" :key="'origin-'+index" class="place-info">
                <h5>{{ place.title }}</h5>
                <p>{{ place.summary }}</p>
                <a :href="place.url" target="_blank">查看更多信息</a>
              </div>
            </div>
            
            <h3>对面位置</h3>
            <p>纬度: {{ antipodeCoords.lat.toFixed(2) }}°</p>
            <p>经度: {{ antipodeCoords.lon.toFixed(2) }}°</p>
            <div v-if="antipodeInfo.length > 0">
              <h4>附近地点</h4>
              <div v-for="(place, index) in antipodeInfo" :key="'antipode-'+index" class="place-info">
                <h5>{{ place.title }}</h5>
                <p>{{ place.summary }}</p>
                <a :href="place.url" target="_blank">查看更多信息</a>
              </div>
            </div>
            <div v-else class="no-info">
              <p>这个位置可能是海洋或者人烟稀少的地区，没有找到相关信息</p>
            </div>
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
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import axios from 'axios';
import { getCurrentInstance } from 'vue';

export default {
  name: 'App',
  data() {
    return {
      instance: null,
      scene: null,
      camera: null,
      renderer: null,
      globe: null,
      controls: null,
      originMarker: null,
      antipodeMarker: null,
      connectionLine: null,
      originCoords: { lat: 0, lon: 0 },
      antipodeCoords: { lat: 0, lon: 0 },
      originInfo: [],
      antipodeInfo: [],
      showInfo: false,
      raycaster: null,
      mouse: null
    };
  },
  mounted() {
    this.instance = getCurrentInstance();
    const { proxy } = this.instance;
    proxy.$scene = new THREE.Scene();
    
    this.initThreeJS();
    this.animate();
    window.addEventListener('resize', this.onWindowResize);
    window.addEventListener('contextmenu', this.onRightClick);
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.onWindowResize);
    window.removeEventListener('contextmenu', this.onRightClick);
    this.dispose();
  },
  methods: {
    initThreeJS() {
      // 创建场景 - 使用 proxy.$scene
      this.scene = this.instance.proxy.$scene;
      
      // 创建相机
      this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
      this.camera.position.z = 5;
      
      // 创建渲染器
      this.renderer = new THREE.WebGLRenderer({ antialias: true });
      this.renderer.setSize(window.innerWidth, window.innerHeight);
      document.getElementById('globe').appendChild(this.renderer.domElement);
      
      // 创建控制器
      this.controls = new OrbitControls(this.camera, this.renderer.domElement);
      this.controls.enableDamping = true;
      this.controls.dampingFactor = 0.05;
      
      // 创建地球
      this.createGlobe();
      
      // 初始化射线检测器和鼠标位置
      this.raycaster = new THREE.Raycaster();
      this.mouse = new THREE.Vector2();
      
      // 添加环境光和平行光
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
      this.scene.add(ambientLight);
      
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
      directionalLight.position.set(5, 3, 5);
      this.scene.add(directionalLight);
    },
    
    createGlobe() {
      // 创建地球几何体
      const geometry = new THREE.SphereGeometry(2, 64, 64);
      
      // 加载地球纹理
      const textureLoader = new THREE.TextureLoader();
      const texture = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_atmos_2048.jpg');
      const bumpMap = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_normal_2048.jpg');
      const specularMap = textureLoader.load('https://raw.githubusercontent.com/mrdoob/three.js/dev/examples/textures/planets/earth_specular_2048.jpg');
      
      // 创建材质
      const material = new THREE.MeshPhongMaterial({
        map: texture,
        bumpMap: bumpMap,
        bumpScale: 0.05,
        specularMap: specularMap,
        specular: new THREE.Color('grey'),
        shininess: 5
      });
      
      // 创建地球网格
      this.globe = new THREE.Mesh(geometry, material);
      this.scene.add(this.globe);
    },
    
    createMarker(position, color) {
      const geometry = new THREE.SphereGeometry(0.05, 16, 16);
      const material = new THREE.MeshBasicMaterial({ color: color });
      const marker = new THREE.Mesh(geometry, material);
      marker.position.copy(position);
      return marker;
    },
    
    createConnectionLine(origin, antipode) {
      const points = [];
      points.push(origin);
      points.push(antipode);
      
      // 创建曲线
      const curve = new THREE.CatmullRomCurve3(points);
      const curveGeometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(50));
      const curveMaterial = new THREE.LineBasicMaterial({ color: 0xff0000 });
      const curveLine = new THREE.Line(curveGeometry, curveMaterial);
      
      return curveLine;
    },
    
    latLonToVector3(lat, lon) {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      const x = -(2 * Math.sin(phi) * Math.cos(theta));
      const y = 2 * Math.cos(phi);
      const z = 2 * Math.sin(phi) * Math.sin(theta);
      return new THREE.Vector3(x, y, z);
    },
    
    onRightClick(event) {
      event.preventDefault();
      
      // 计算鼠标在标准化设备坐标中的位置
      this.mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
      this.mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;
      
      // 更新射线检测器
      this.raycaster.setFromCamera(this.mouse, this.camera);
      
      // 检测与地球的交点
      const intersects = this.raycaster.intersectObject(this.globe);
      
      if (intersects.length > 0) {
        const point = intersects[0].point;
        const lat = Math.asin(point.y / 2) * (180 / Math.PI);
        const lon = Math.atan2(point.z, -point.x) * (180 / Math.PI) - 180;
        
        // 更新坐标
        this.originCoords = { lat, lon };
        
        // 计算对面位置
        const antipodeLat = -lat;
        const antipodeLon = lon <= 0 ? lon + 180 : lon - 180;
        this.antipodeCoords = { lat: antipodeLat, lon: antipodeLon };
        
        // 创建标记
        if (this.originMarker) {
          this.scene.remove(this.originMarker);
        }
        if (this.antipodeMarker) {
          this.scene.remove(this.antipodeMarker);
        }
        if (this.connectionLine) {
          this.scene.remove(this.connectionLine);
        }
        
        this.originMarker = this.createMarker(point, 0xff0000);
        const antipodePoint = this.latLonToVector3(antipodeLat, antipodeLon);
        this.antipodeMarker = this.createMarker(antipodePoint, 0xff0000);
        
        this.connectionLine = this.createConnectionLine(point, antipodePoint);
        
        this.scene.add(this.originMarker);
        this.scene.add(this.antipodeMarker);
        this.scene.add(this.connectionLine);
        
        // 获取位置信息
        this.getLocationInfo(lat, lon);
        
        // 显示信息面板
        this.showInfo = true;
      }
    },
    
    getLocationInfo(lat, lon) {
      // 获取原始位置信息
      axios.get(`http://localhost:5000/api/antipode?lat=${lat}&lon=${lon}`)
        .then(response => {
          this.originInfo = response.data.origin.info;
          this.antipodeInfo = response.data.antipode.info;
        })
        .catch(error => {
          console.error('Error fetching location info:', error);
        });
    },
    
    onWindowResize() {
      this.camera.aspect = window.innerWidth / window.innerHeight;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(window.innerWidth, window.innerHeight);
    },
    
    animate() {
      requestAnimationFrame(this.animate);
      this.controls.update();
      
      // 使用 instance.proxy 渲染场景
      const scene = this.instance.proxy.$scene;
      this.renderer.render(scene, this.camera);
    },
    
    // 添加截图功能，按照解决方案的示例
    snapShot() {
      const camera = this.camera;
      if(!camera) return;
      const scene = this.instance.proxy.$scene;
      const strMime = "image/png";
      const renderer = this.renderer;
      renderer.render(scene, camera);
      const canvas = this.renderer.domElement;
      return canvas.toDataURL(strMime);
    },
    
    dispose() {
      this.renderer.dispose();
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
  background-color: #000;
  overflow: hidden;
}

.app-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  text-align: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
}

header h1 {
  font-size: 2rem;
  margin-bottom: 10px;
}

.instructions {
  font-size: 1rem;
  opacity: 0.8;
}

.globe-container {
  flex: 1;
  position: relative;
}

#globe {
  width: 100%;
  height: 100%;
}

.info-panel {
  position: fixed;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  width: 300px;
  max-height: 80vh;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 8px;
  padding: 20px;
  overflow-y: auto;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.info-content h3 {
  color: #2c3e50;
  margin-bottom: 15px;
}

.info-content p {
  margin-bottom: 10px;
  color: #666;
}

.place-info {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #eee;
}

.place-info h5 {
  color: #3498db;
  margin-bottom: 10px;
}

.place-info p {
  margin-bottom: 10px;
  font-size: 0.9rem;
}

.place-info a {
  color: #3498db;
  text-decoration: none;
  font-size: 0.9rem;
}

.place-info a:hover {
  text-decoration: underline;
}

.no-info {
  padding: 15px;
  background-color: #f9f9f9;
  border-radius: 4px;
  color: #666;
  font-size: 0.9rem;
}

footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  text-align: center;
  padding: 10px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  z-index: 100;
}
</style>









