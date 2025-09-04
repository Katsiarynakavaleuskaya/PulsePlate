import { useState } from 'react'
import './App.css'

function App() {
  const [height, setHeight] = useState(170)
  const [weight, setWeight] = useState(65)
  const [age, setAge] = useState(30)
  const [sex, setSex] = useState<'male' | 'female'>('female')
  const [goal, setGoal] = useState<'lose' | 'maintain' | 'gain'>('maintain')
  const [activity, setActivity] = useState<'low' | 'moderate' | 'high'>('moderate')
  const [bmi, setBmi] = useState<number | null>(null)
  const [tdee, setTdee] = useState<number | null>(null)

  const calculateBMI = () => {
    const heightInMeters = height / 100
    const bmiValue = weight / (heightInMeters * heightInMeters)
    setBmi(parseFloat(bmiValue.toFixed(1)))
  }

  const calculateTDEE = () => {
    // Simplified Mifflin-St Jeor Equation
    let bmr
    if (sex === 'male') {
      bmr = 10 * weight + 6.25 * height - 5 * age + 5
    } else {
      bmr = 10 * weight + 6.25 * height - 5 * age - 161
    }

    const activityMultiplier = {
      low: 1.2,
      moderate: 1.55,
      high: 1.9
    }[activity]

    const tdeeValue = bmr * activityMultiplier
    setTdee(Math.round(tdeeValue))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    calculateBMI()
    calculateTDEE()
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>PulsePlate</h1>
        <p>Nutrition • Body • Lifestyle</p>
      </header>

      <main className="app-main">
        <section className="input-section card">
          <h2>My Plate</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="height">Height (cm)</label>
              <input
                id="height"
                type="number"
                value={height}
                onChange={(e) => setHeight(Number(e.target.value))}
                min="100"
                max="250"
              />
            </div>

            <div className="form-group">
              <label htmlFor="weight">Weight (kg)</label>
              <input
                id="weight"
                type="number"
                value={weight}
                onChange={(e) => setWeight(Number(e.target.value))}
                min="30"
                max="200"
              />
            </div>

            <div className="form-group">
              <label htmlFor="age">Age</label>
              <input
                id="age"
                type="number"
                value={age}
                onChange={(e) => setAge(Number(e.target.value))}
                min="15"
                max="100"
              />
            </div>

            <div className="form-group">
              <label htmlFor="sex">Sex</label>
              <select
                id="sex"
                value={sex}
                onChange={(e) => setSex(e.target.value as 'male' | 'female')}
              >
                <option value="female">Female</option>
                <option value="male">Male</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="goal">Goal</label>
              <select
                id="goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value as 'lose' | 'maintain' | 'gain')}
              >
                <option value="lose">Lose Weight</option>
                <option value="maintain">Maintain Weight</option>
                <option value="gain">Gain Weight</option>
              </select>
            </div>

            <div className="form-group">
              <label htmlFor="activity">Activity Level</label>
              <select
                id="activity"
                value={activity}
                onChange={(e) => setActivity(e.target.value as 'low' | 'moderate' | 'high')}
              >
                <option value="low">Low</option>
                <option value="moderate">Moderate</option>
                <option value="high">High</option>
              </select>
            </div>

            <button type="submit">Calculate</button>
          </form>
        </section>

        {(bmi !== null || tdee !== null) && (
          <section className="results-section">
            <div className="card">
              <h2>Results</h2>
              {bmi !== null && (
                <div className="result-item">
                  <h3>BMI</h3>
                  <p className="result-value">{bmi}</p>
                  <p className="result-description">
                    {bmi < 18.5 ? 'Underweight' : bmi < 25 ? 'Normal' : bmi < 30 ? 'Overweight' : 'Obese'}
                  </p>
                </div>
              )}
              {tdee !== null && (
                <div className="result-item">
                  <h3>TDEE</h3>
                  <p className="result-value">{tdee} kcal</p>
                  <p className="result-description">
                    {goal === 'lose' 
                      ? `Recommended: ${Math.round(tdee * 0.8)} kcal (20% deficit)` 
                      : goal === 'gain' 
                      ? `Recommended: ${Math.round(tdee * 1.1)} kcal (10% surplus)` 
                      : `Maintain at ${tdee} kcal`}
                  </p>
                </div>
              )}
            </div>

            <div className="card plate-visualization">
              <h2>Your Plate</h2>
              <div className="plate-container">
                <div className="plate">
                  <div className="plate-center">
                    <div className="plate-glow"></div>
                  </div>
                  <div className="plate-item protein">Protein</div>
                  <div className="plate-item carbs">Carbs</div>
                  <div className="plate-item fats">Fats</div>
                  <div className="plate-item vegetables">Vegetables</div>
                </div>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App